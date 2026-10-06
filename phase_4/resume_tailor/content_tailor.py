"""
content_tailor.py — Optional Gemini-based tailoring plan generator.

ARCHITECTURE:
    Gemini receives structured profile data + JD match info.
    Gemini returns a TailoringPlan (JSON) — NOT LaTeX, NOT free-form text.
    Python code constructs the actual resume from that data.

HALLUCINATION PROTECTION:
    Every item in TailoringPlan.skills_to_emphasize is validated against the
    user's actual profile skills before use. Any fabricated skill is dropped.
    Every project_id must exist in the Phase 3 ranked list.

FALLBACK:
    If Gemini is unavailable or fails, a deterministic plan is returned:
    - Top-N projects by Phase 3 score
    - Skills matched in Phase 3 are emphasized
    - Summary is unchanged
"""

from __future__ import annotations

import json
import logging
import time
from typing import List, Optional

from phase_4.resume_tailor.config import config
from phase_4.resume_tailor.schemas import TailoringPlan

logger = logging.getLogger(__name__)


# ── System prompt ─────────────────────────────────────────────────────────────

TAILORING_SYSTEM_PROMPT = """\
You are a Resume Tailoring Advisor.

Your job is to analyse a Job Description analysis and a user's profile, then produce
a structured tailoring plan so the user's resume can be tailored for that specific job.

STRICT RULES:
1. You MUST NOT invent new skills, technologies, certifications, or experience.
2. You MUST NOT add skills the user does not have.
3. skills_to_emphasize MUST be a strict subset of the actual profile skills provided.
4. summary_focus MUST be skills/technologies the user actually possesses.
5. project_ids MUST be a strict subset of the candidate_project_ids provided.
6. Do NOT fabricate: experience years, metrics, job titles, tools, or achievements.
7. Return ONLY the structured JSON output — no additional text.
"""


def _build_tailoring_prompt(
    profile: dict,
    jd_data: dict,
    match_result: dict,
    skills_grouped: dict[str, list[str]],
    ranked_project_ids: List[str],
    all_projects_by_id: dict[str, dict],
    project_limit: int,
) -> str:
    """Build the Gemini prompt for tailoring plan generation."""
    jd_analysis = jd_data.get("analysis", jd_data)
    job_title = match_result.get("job_title", jd_analysis.get("job_title", ""))
    
    # Flatten all profile skills
    all_skills = [s for lst in skills_grouped.values() for s in lst]

    # Describe available candidate projects (only those ranked by Phase 3)
    project_descriptions = []
    for pid in ranked_project_ids:
        proj = all_projects_by_id.get(pid, {})
        if proj:
            project_descriptions.append(
                f"  - ID: {pid}\n"
                f"    Name: {proj.get('name', 'Unknown')}\n"
                f"    Technologies: {', '.join(proj.get('technologies', []) or [])}\n"
                f"    Keywords: {', '.join(proj.get('keywords', []) or [])}"
            )

    return f"""\
### JOB DESCRIPTION ANALYSIS
Job Title: {job_title}
Role Category: {jd_analysis.get('role_category', 'Unspecified')}
Required Skills: {', '.join(jd_analysis.get('required_skills', []))}
Preferred Skills: {', '.join(jd_analysis.get('preferred_skills', []))}
Technologies: {', '.join(jd_analysis.get('technologies', []))}

### USER PROFILE
Original Summary: {profile.get('summary', '')}
All Profile Skills: {', '.join(all_skills)}

### PHASE 3 MATCH RESULT
Matched Required Skills: {', '.join(match_result.get('matched_required_skills', []) or [])}
Matched Technologies: {', '.join(match_result.get('matched_technologies', []) or [])}
Missing Required Skills: {', '.join(match_result.get('missing_required_skills', []) or [])}

### CANDIDATE PROJECTS (Phase 3 ranked, best first)
{chr(10).join(project_descriptions)}

### TASK
Produce a tailoring plan. Select up to {project_limit} project_ids from the candidates above.
summary_focus should list existing profile skills to highlight in the summary.
skills_to_emphasize should list skills from "All Profile Skills" to move to the front.
Do NOT include any skill not in "All Profile Skills".
Do NOT include any project_id not in the candidate list.
"""


class ContentTailor:
    """
    Generates a TailoringPlan using Gemini, with deterministic fallback.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self._api_key = api_key or config.GEMINI_API_KEY
        self._model   = model   or config.GEMINI_MODEL
        self._client  = None

        if self._api_key:
            try:
                from google import genai
                from google.genai import types as genai_types
                self._client = genai.Client(api_key=self._api_key)
                self._types  = genai_types
            except ImportError:
                logger.warning(
                    "google-genai package not installed. Using deterministic tailoring."
                )
        else:
            logger.warning(
                "GEMINI_API_KEY not set. Using deterministic tailoring fallback."
            )

    def plan(
        self,
        profile: dict,
        jd_data: dict,
        match_result: dict,
        skills_grouped: dict[str, list[str]],
        ranked_project_ids: List[str],
        all_projects_by_id: dict[str, dict],
        project_limit: int = 3,
    ) -> TailoringPlan:
        """
        Produce a TailoringPlan.

        If Gemini is available, calls the API and validates the response.
        Falls back to a deterministic plan on any failure.
        """
        if self._client is None:
            logger.info("Using deterministic tailoring plan (no Gemini client).")
            return self._deterministic_plan(
                match_result, ranked_project_ids, project_limit
            )

        last_exc: Optional[Exception] = None
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                logger.info(
                    "Calling Gemini for tailoring plan (attempt %d/%d)...",
                    attempt, config.MAX_RETRIES,
                )
                raw_plan = self._call_gemini(
                    profile=profile,
                    jd_data=jd_data,
                    match_result=match_result,
                    skills_grouped=skills_grouped,
                    ranked_project_ids=ranked_project_ids,
                    all_projects_by_id=all_projects_by_id,
                    project_limit=project_limit,
                )
                validated = self._validate_plan(
                    plan=raw_plan,
                    skills_grouped=skills_grouped,
                    ranked_project_ids=ranked_project_ids,
                    project_limit=project_limit,
                )
                return validated
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning("Gemini tailoring plan attempt %d failed: %s", attempt, exc)
                if attempt < config.MAX_RETRIES:
                    time.sleep(2 ** (attempt - 1))

        logger.error(
            "All %d Gemini tailoring attempts failed (last: %s). "
            "Using deterministic fallback.",
            config.MAX_RETRIES, last_exc,
        )
        return self._deterministic_plan(
            match_result, ranked_project_ids, project_limit
        )

    def _call_gemini(
        self,
        profile: dict,
        jd_data: dict,
        match_result: dict,
        skills_grouped: dict[str, list[str]],
        ranked_project_ids: List[str],
        all_projects_by_id: dict[str, dict],
        project_limit: int,
    ) -> TailoringPlan:
        """Call Gemini and parse structured TailoringPlan response."""
        prompt = _build_tailoring_prompt(
            profile=profile,
            jd_data=jd_data,
            match_result=match_result,
            skills_grouped=skills_grouped,
            ranked_project_ids=ranked_project_ids,
            all_projects_by_id=all_projects_by_id,
            project_limit=project_limit,
        )

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=self._types.GenerateContentConfig(
                system_instruction=TAILORING_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=TailoringPlan,
                temperature=0.1,
            ),
        )

        if hasattr(response, "parsed") and response.parsed is not None:
            parsed = response.parsed
            if isinstance(parsed, TailoringPlan):
                return parsed
            return TailoringPlan.model_validate(parsed)

        # Fallback: parse from raw text
        raw_text = response.text
        if not raw_text:
            raise RuntimeError("Gemini returned empty tailoring plan.")
        data = json.loads(raw_text)
        return TailoringPlan.model_validate(data)

    def _validate_plan(
        self,
        plan: TailoringPlan,
        skills_grouped: dict[str, list[str]],
        ranked_project_ids: List[str],
        project_limit: int,
    ) -> TailoringPlan:
        """
        Hallucination protection layer.

        Removes any skills not in the real profile and any project IDs
        not in the Phase 3 ranked list.
        """
        # Flatten all real profile skills (lowercase set for comparison)
        real_skills_norm = {
            s.strip().lower()
            for lst in skills_grouped.values()
            for s in lst
        }
        valid_pids = set(ranked_project_ids)

        # Validate summary_focus
        valid_summary_focus = [
            s for s in plan.summary_focus
            if s.strip().lower() in real_skills_norm
        ]
        rejected_focus = set(plan.summary_focus) - set(valid_summary_focus)
        if rejected_focus:
            logger.warning(
                "Gemini hallucinated summary_focus skills (not in profile): %s — removed.",
                rejected_focus,
            )

        # Validate skills_to_emphasize
        valid_skills = [
            s for s in plan.skills_to_emphasize
            if s.strip().lower() in real_skills_norm
        ]
        rejected_skills = set(plan.skills_to_emphasize) - set(valid_skills)
        if rejected_skills:
            logger.warning(
                "Gemini hallucinated skills_to_emphasize (not in profile): %s — removed.",
                rejected_skills,
            )

        # Validate project_ids — must be in Phase 3 ranked list, capped at limit
        valid_pids_ordered = [
            pid for pid in plan.project_ids
            if pid in valid_pids
        ][:project_limit]
        rejected_pids = set(plan.project_ids) - set(valid_pids_ordered)
        if rejected_pids:
            logger.warning(
                "Gemini returned unknown/excess project IDs: %s — removed.",
                rejected_pids,
            )

        # If Gemini returned too few project IDs, fill with top-ranked ones
        if len(valid_pids_ordered) < project_limit:
            for pid in ranked_project_ids:
                if pid not in set(valid_pids_ordered):
                    valid_pids_ordered.append(pid)
                if len(valid_pids_ordered) >= project_limit:
                    break

        return TailoringPlan(
            summary_focus=valid_summary_focus,
            skills_to_emphasize=valid_skills,
            project_ids=valid_pids_ordered,
            tailoring_notes=plan.tailoring_notes,
        )

    def _deterministic_plan(
        self,
        match_result: dict,
        ranked_project_ids: List[str],
        project_limit: int,
    ) -> TailoringPlan:
        """
        Deterministic fallback when Gemini is unavailable or fails.

        Uses Phase 3 matched skills for emphasis and top-N ranked projects.
        """
        matched_required = match_result.get("matched_required_skills") or []
        matched_tech     = match_result.get("matched_technologies") or []
        matched_preferred = match_result.get("matched_preferred_skills") or []

        # Deduplicate while preserving order
        seen: set[str] = set()
        skills_to_emphasize: List[str] = []
        for s in (matched_required + matched_tech + matched_preferred):
            if s and s.lower() not in seen:
                skills_to_emphasize.append(s)
                seen.add(s.lower())

        return TailoringPlan(
            summary_focus=matched_required[:5],   # emphasise up to 5 required skills
            skills_to_emphasize=skills_to_emphasize,
            project_ids=ranked_project_ids[:project_limit],
            tailoring_notes="Deterministic tailoring plan (Gemini not used).",
        )
