"""
deduplicator.py — Long-term deterministic deduplication for Phase 6.2.

Design:
  All deduplication is performed via targeted Firestore indexed queries
  (where("field", "==", value).limit(1)) rather than loading a sliding
  window of recent documents.  This guarantees correct deduplication
  regardless of how many jobs are stored.

  Five deduplication levels — each stored as its own indexed document field:

  L1  canonical_url         — normalized application URL
  L2  telegram_message_key  — telegram:{channel}:{message_id}
  L3  content_hash          — SHA-256(company|title|description[:300])
  L4  job_identity_key      — MD5(company:title:location) — only when all present

  Source metadata merging is unchanged from Phase 6.0.
"""

from __future__ import annotations
import hashlib
import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs

from phase_6.models.opportunity import JobOpportunity

# UTM-style tracking parameters to strip from canonical URLs
_UTM_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "utm_id", "fbclid", "gclid", "ref", "referrer", "source",
    "mc_cid", "mc_eid",
})


class JobDeduplicator:
    """
    Computes deterministic deduplication keys for storage in Firestore,
    and provides source metadata merging for duplicate discoveries.
    """

    # ── Key Computation ──────────────────────────────────────────────────────

    @staticmethod
    def compute_canonical_url(url: Optional[str]) -> Optional[str]:
        """
        Normalizes a URL for deduplication purposes.

        Stripping:
          - trailing slash from the path
          - URL fragment (#section)
          - common UTM / tracking query parameters

        NOT stripping:
          - path components that distinguish different jobs
          - meaningful query parameters (e.g. job IDs)

        Returns None if the URL is empty or malformed.
        """
        if not url or not url.strip():
            return None

        url = url.strip()

        try:
            parsed = urlparse(url)
        except Exception:
            return None

        # Only accept http/https URLs
        if parsed.scheme not in ("http", "https"):
            return None

        # Strip fragment
        fragment = ""

        # Strip known tracking parameters; preserve everything else
        qs = parse_qs(parsed.query, keep_blank_values=True)
        filtered_qs = {k: v for k, v in qs.items() if k.lower() not in _UTM_PARAMS}

        # Re-encode query string (sorted for determinism)
        new_query = urlencode(sorted(filtered_qs.items()), doseq=True)

        # Normalize path — remove trailing slash ONLY if path has content beyond "/"
        path = parsed.path
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")

        # Lowercase scheme + netloc for case-insensitivity; preserve path case
        canonical = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            parsed.params,
            new_query,
            fragment
        ))
        return canonical if canonical else None

    @staticmethod
    def compute_telegram_message_key(channel: Optional[str], message_id: Optional[int]) -> Optional[str]:
        """
        Constructs a stable, unique key for a single Telegram message.

        Format: telegram:{normalized_channel}:{message_id}

        Example:
            @pythonjobspune + 9001  →  telegram:pythonjobspune:9001

        Returns None if either value is missing.
        """
        if not channel or not message_id:
            return None
        # Normalize: strip '@', lowercase
        normalized_channel = channel.lstrip("@").lower().strip()
        if not normalized_channel:
            return None
        return f"telegram:{normalized_channel}:{message_id}"

    @staticmethod
    def compute_content_hash(company: str, job_title: str, description: str) -> str:
        """
        SHA-256 hash of normalized company + title + first 300 chars of description.
        Unchanged from Phase 6.0 — stored as 'content_hash' in Firestore.
        """
        norm_company = (company or "").lower().strip()
        norm_title = (job_title or "").lower().strip()
        norm_desc = (description or "")[:300].lower().strip()
        # Normalize whitespace
        norm_desc = re.sub(r"\s+", " ", norm_desc)
        payload = f"{norm_company}|{norm_title}|{norm_desc}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_job_identity_key(company: Optional[str], job_title: Optional[str], location: Optional[str]) -> Optional[str]:
        """
        MD5 of normalized company:title:location.

        Returns None if any of company or job_title is empty — we must not
        merge jobs when company or title is unknown.

        Example:
            "XYZ Technologies", "Python Developer", "Pune"
            → md5("xyz technologies:python developer:pune")
        """
        norm_company = (company or "").lower().strip()
        norm_title = (job_title or "").lower().strip()
        norm_location = (location or "").lower().strip()

        # Require at least company AND title to be non-empty
        if not norm_company or not norm_title:
            return None

        payload = f"{norm_company}:{norm_title}:{norm_location}"
        return hashlib.md5(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def find_duplicate(
        candidate: JobOpportunity,
        existing_opportunities: List[JobOpportunity]
    ) -> Optional[JobOpportunity]:
        """
        Compares candidate opportunity against a list of existing opportunities.
        Restored to maintain 100% backward compatibility with legacy unit tests.
        """
        # Calculate keys for candidate
        cand_url = candidate.canonical_url or JobDeduplicator.compute_canonical_url(candidate.application_url)
        cand_tg_key = candidate.telegram_message_key or JobDeduplicator.compute_telegram_message_key(candidate.source_channel, candidate.source_message_id)
        cand_hash = candidate.content_hash or JobDeduplicator.compute_content_hash(candidate.company, candidate.job_title, candidate.description)
        cand_ident = candidate.job_identity_key or JobDeduplicator.compute_job_identity_key(candidate.company, candidate.job_title, candidate.location)

        for existing in existing_opportunities:
            # L1 URL Check
            exist_url = existing.canonical_url or JobDeduplicator.compute_canonical_url(existing.application_url)
            if cand_url and exist_url and cand_url == exist_url:
                return existing

            # L2 Telegram Message Key Check
            exist_tg_key = existing.telegram_message_key or JobDeduplicator.compute_telegram_message_key(existing.source_channel, existing.source_message_id)
            if cand_tg_key and exist_tg_key and cand_tg_key == exist_tg_key:
                return existing

            # L3 Content Hash Check
            exist_hash = existing.content_hash or JobDeduplicator.compute_content_hash(existing.company, existing.job_title, existing.description)
            if cand_hash and exist_hash and cand_hash == exist_hash:
                return existing

            # L4 Job Identity Key Check
            exist_ident = existing.job_identity_key or JobDeduplicator.compute_job_identity_key(existing.company, existing.job_title, existing.location)
            if cand_ident and exist_ident and cand_ident == exist_ident:
                return existing

        return None

    # ── Source Metadata Merging ──────────────────────────────────────────────

    @staticmethod
    def merge_source_metadata(existing_data: Dict[str, Any], new_item: JobOpportunity) -> Dict[str, Any]:
        """
        Appends a new source reference to the canonical job's sources[] array.
        Idempotent — skips if the exact same source reference is already recorded.
        """
        sources = existing_data.get("sources", [])

        new_source_ref = {
            "source": new_item.source,
            "source_type": new_item.source_type,
            "source_name": new_item.source_name,
            "source_channel": new_item.source_channel,
            "source_message_id": new_item.source_message_id,
            "source_url": new_item.source_url,
            "discovered_at": new_item.discovered_at
        }

        # Idempotency: check if this exact source reference already exists
        already_exists = False
        for s in sources:
            if s.get("source") == new_item.source:
                if new_item.source == "telegram":
                    if (s.get("source_channel") == new_item.source_channel and
                            s.get("source_message_id") == new_item.source_message_id):
                        already_exists = True
                        break
                elif s.get("source_url") == new_item.source_url:
                    already_exists = True
                    break

        if not already_exists:
            sources.append(new_source_ref)

        existing_data["sources"] = sources
        existing_data["ingestion_status"] = "STORED"
        return existing_data
