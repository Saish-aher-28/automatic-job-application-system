"""
project_selector.py — Selects projects for the tailored resume.

Selection strategy:
  1. Primary signal: Phase 3 final_project_score (descending).
  2. Respect PROJECT_SELECT_LIMIT (default 3).
  3. Coverage diversity check: if the top-N projects share all the same
     key technologies from the JD, and a lower-ranked project introduces
     a new required technology, it may be swapped in.
  4. NEVER invents new projects or adds projects not in Phase 3's list.
  5. Returns a list of Firestore project _id strings (ordered by score).

The caller is responsible for fetching the full project documents from Firestore.
"""

from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger(__name__)


def _normalise(name: str) -> str:
    """Lowercase + strip for technology comparison."""
    return name.strip().lower()


def select_projects(
    ranked_projects: List[dict],
    all_projects_by_id: dict[str, dict],
    required_technologies: List[str],
    limit: int = 3,
) -> List[str]:
    """
    Select up to `limit` project IDs from the Phase 3 ranked list.

    Args:
        ranked_projects: List of Phase 3 ProjectMatchDetail-like dicts, each with:
                         {'project_id': str, 'project_name': str,
                          'final_project_score': float, ...}
                         Assumed to be pre-sorted descending by final_project_score.
        all_projects_by_id: Mapping of project _id → full project dict (from Firestore).
        required_technologies: JD required technologies (from Phase 2/3 analysis).
        limit: Maximum number of projects to select.

    Returns:
        List of project _id strings in selection order (best first).
    """
    if not ranked_projects:
        logger.warning("No ranked projects provided for selection.")
        return []

    limit = max(1, limit)

    # ── Step 1: Take top-N by Phase 3 score ──────────────────────────────────
    candidates = ranked_projects[:limit]
    selected_ids = [p["project_id"] for p in candidates]

    # ── Step 2: Coverage diversity check ─────────────────────────────────────
    # Only apply when we have more projects available than the limit AND
    # there are required technologies to check against.
    if len(ranked_projects) > limit and required_technologies:
        selected_ids = _apply_coverage_diversity(
            selected_ids=selected_ids,
            ranked_projects=ranked_projects,
            all_projects_by_id=all_projects_by_id,
            required_technologies=required_technologies,
            limit=limit,
        )

    logger.info(
        "Selected %d project(s): %s",
        len(selected_ids),
        [all_projects_by_id.get(pid, {}).get("name", pid) for pid in selected_ids],
    )
    return selected_ids


def _apply_coverage_diversity(
    selected_ids: List[str],
    ranked_projects: List[dict],
    all_projects_by_id: dict[str, dict],
    required_technologies: List[str],
    limit: int,
) -> List[str]:
    """
    Check if a lower-ranked project provides a required technology that the
    current selection is entirely missing. If so, swap in that project for
    the lowest-scoring selected project.

    At most one swap is performed to keep the selection stable.
    """
    req_techs_norm = {_normalise(t) for t in required_technologies if t}

    # Technologies covered by the current selection
    covered_techs: set[str] = set()
    for pid in selected_ids:
        proj = all_projects_by_id.get(pid, {})
        for tech in proj.get("technologies", []) or []:
            if tech:
                covered_techs.add(_normalise(tech))

    # Technologies the current selection is missing
    uncovered = req_techs_norm - covered_techs
    if not uncovered:
        return selected_ids  # full coverage, no swap needed

    # Find the best alternative (highest Phase 3 score) that covers at least
    # one uncovered technology and is not already selected.
    already_selected = set(selected_ids)
    remaining = [p for p in ranked_projects[limit:] if p["project_id"] not in already_selected]

    best_alt = None
    best_alt_coverage = 0
    for rp in remaining:
        proj = all_projects_by_id.get(rp["project_id"], {})
        proj_techs = {_normalise(t) for t in proj.get("technologies", []) or [] if t}
        new_coverage = len(proj_techs & uncovered)
        if new_coverage > best_alt_coverage:
            best_alt = rp
            best_alt_coverage = new_coverage

    if best_alt is None:
        return selected_ids  # no better alternative found

    # Swap out the lowest-scoring selected project
    # (last item, since Phase 3 list is sorted descending)
    replaced_id = selected_ids[-1]
    replaced_proj = all_projects_by_id.get(replaced_id, {})
    new_proj = all_projects_by_id.get(best_alt["project_id"], {})

    logger.info(
        "Coverage diversity: swapping '%s' (score %.1f) for '%s' (score %.1f) "
        "to cover required technologies: %s",
        replaced_proj.get("name", replaced_id),
        ranked_projects[len(selected_ids) - 1].get("final_project_score", 0),
        new_proj.get("name", best_alt["project_id"]),
        best_alt.get("final_project_score", 0),
        ", ".join(sorted(uncovered)),
    )

    result = selected_ids[:-1] + [best_alt["project_id"]]
    return result


def build_projects_by_id_map(all_projects: List[dict]) -> dict[str, dict]:
    """
    Build a {_id: project_dict} mapping from a list of project dicts.
    Convenience function used by the pipeline.
    """
    return {p["_id"]: p for p in all_projects if p.get("_id")}
