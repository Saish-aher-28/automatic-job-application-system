"""
matcher.py — Main matching orchestrator.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from phase_3.matcher.config import config
from phase_3.matcher.schemas import JobMatchResult, ProjectMatchDetail
from phase_3.matcher.skill_matcher import match_skills_and_technologies
from phase_3.matcher.project_matcher import calculate_project_preliminary_score
from phase_3.matcher.semantic_matcher import SemanticMatcher
from phase_3.matcher.scorer import calculate_project_final_score, calculate_overall_match_score

logger = logging.getLogger(__name__)


class JDProfileMatcher:
    """
    Main matching engine mapping a JD analysis to a user profile.
    """

    def __init__(self, semantic_matcher: Optional[SemanticMatcher] = None) -> None:
        # Lazy initialization of semantic matcher
        self._semantic_matcher = semantic_matcher

    def match(
        self,
        jd_document_id: str,
        jd_data: dict,
        profile_data: dict,
        skills: List[str],
        projects: List[dict],
    ) -> JobMatchResult:
        """
        Orchestrates the matching pipeline.

        Args:
            jd_document_id: Unique identifier of the JD document.
            jd_data: The structured analysis dict of the JD (from Phase 2).
            profile_data: User profile dict.
            skills: List of user skills.
            projects: List of all user projects.

        Returns:
            JobMatchResult containing scores and details.
        """
        logger.info("Starting JD ↔ Profile Match for JD ID: %s", jd_document_id)

        # ── 1. Extract JD fields ──
        jd_analysis      = jd_data.get("analysis", {})
        job_title        = jd_analysis.get("job_title", "Untitled Position") or "Untitled Position"
        jd_required      = jd_analysis.get("required_skills", []) or []
        jd_preferred     = jd_analysis.get("preferred_skills", []) or []
        jd_technologies  = jd_analysis.get("technologies", []) or []
        jd_keywords      = jd_analysis.get("keywords", []) or []
        jd_role_category = jd_analysis.get("role_category", None)

        # ── 2. Gather user information ──
        # Gather all unique technologies listed across all active user projects
        user_project_techs_set = set()
        for p in projects:
            for t in p.get("technologies", []):
                if t:
                    user_project_techs_set.add(t.strip())
        user_project_techs = sorted(list(user_project_techs_set))

        # ── 3. Run Skill & Technology Matching ──
        logger.info("Matching profile skills against JD requirements...")
        skill_match_res = match_skills_and_technologies(
            jd_required=jd_required,
            jd_preferred=jd_preferred,
            jd_technologies=jd_technologies,
            user_skills=skills,
            user_project_technologies=user_project_techs,
        )

        # ── 4. Stage 1: Deterministic Project Scoring ──
        logger.info("Stage 1: Running deterministic project matching...")
        prelim_details = []
        for p in projects:
            p_id = p.get("_id") or p.get("name") or "unknown"
            scores_and_matches = calculate_project_preliminary_score(
                project=p,
                jd_required=jd_required,
                jd_preferred=jd_preferred,
                jd_technologies=jd_technologies,
                jd_keywords=jd_keywords,
                jd_role_category=jd_role_category,
            )
            prelim_details.append((p, scores_and_matches))

        # Sort projects descending by preliminary score
        prelim_details.sort(key=lambda item: item[1]["preliminary_score"], reverse=True)

        # ── 5. Stage 2: Gemini Semantic Matching for top candidates ──
        # Determine candidates for semantic matching
        limit = config.SEMANTIC_PROJECT_CANDIDATES
        semantic_candidates = prelim_details[:limit]
        remaining_candidates = prelim_details[limit:]

        ranked_projects: List[ProjectMatchDetail] = []

        # Lazy initialize semantic matcher if not passed
        if self._semantic_matcher is None and len(semantic_candidates) > 0:
            try:
                self._semantic_matcher = SemanticMatcher()
            except Exception as exc:
                logger.error("Could not initialize SemanticMatcher: %s", exc)

        # Run semantic evaluation
        for p, details in semantic_candidates:
            semantic_score = None
            reason = "Deterministically evaluated."

            if self._semantic_matcher is not None:
                try:
                    eval_result = self._semantic_matcher.evaluate_project_relevance(
                        jd_analysis, p
                    )
                    semantic_score = eval_result.relevance_score
                    reason = eval_result.reason
                except Exception as exc:
                    logger.warning(
                        "Semantic evaluation failed for project '%s': %s. "
                        "Falling back to deterministic score.",
                        p.get("name"), exc
                    )
                    reason = f"Deterministic match (Semantic call failed: {exc})"
            else:
                reason = "Deterministic match (Gemini API not configured/available)."

            final_project_score = calculate_project_final_score(
                details["preliminary_score"], semantic_score
            )

            ranked_projects.append(
                ProjectMatchDetail(
                    project_id=p.get("_id", "unknown"),
                    project_name=p.get("name", "Untitled Project"),
                    preliminary_score=details["preliminary_score"],
                    semantic_score=semantic_score,
                    final_project_score=final_project_score,
                    matched_skills=details["matched_skills"],
                    matched_technologies=details["matched_technologies"],
                    missing_relevant_skills=details["missing_relevant_skills"],
                    reason=reason,
                )
            )

        # Process the remaining projects (purely deterministic score)
        for p, details in remaining_candidates:
            final_project_score = calculate_project_final_score(
                details["preliminary_score"], None
            )

            ranked_projects.append(
                ProjectMatchDetail(
                    project_id=p.get("_id", "unknown"),
                    project_name=p.get("name", "Untitled Project"),
                    preliminary_score=details["preliminary_score"],
                    semantic_score=None,
                    final_project_score=final_project_score,
                    matched_skills=details["matched_skills"],
                    matched_technologies=details["matched_technologies"],
                    missing_relevant_skills=details["missing_relevant_skills"],
                    reason="Deterministically evaluated (outside top candidates limit).",
                )
            )

        # Re-sort all projects descending by final project score
        ranked_projects.sort(key=lambda x: x.final_project_score, reverse=True)

        # ── 6. Calculate Overall Match Score ──
        logger.info("Calculating final match scores...")
        project_scores = [rp.final_project_score for rp in ranked_projects]

        overall_score = calculate_overall_match_score(
            required_score=skill_match_res["required_skill_match_score"],
            preferred_score=skill_match_res["preferred_skill_match_score"],
            tech_score=skill_match_res["technology_match_score"],
            project_scores=project_scores,
        )

        # Top N projects average for overall match metadata
        top_scores = project_scores[:3]
        project_relevance_score = round(sum(top_scores) / len(top_scores), 1) if top_scores else 0.0

        # ── 7. Construct final result model ──
        return JobMatchResult(
            jd_document_id=jd_document_id,
            job_title=job_title,
            overall_match_score=overall_score,
            required_skill_match_score=skill_match_res["required_skill_match_score"],
            preferred_skill_match_score=skill_match_res["preferred_skill_match_score"],
            technology_match_score=skill_match_res["technology_match_score"],
            project_relevance_score=project_relevance_score,
            matched_required_skills=skill_match_res["matched_required_skills"],
            missing_required_skills=skill_match_res["missing_required_skills"],
            matched_preferred_skills=skill_match_res["matched_preferred_skills"],
            missing_preferred_skills=skill_match_res["missing_preferred_skills"],
            matched_technologies=skill_match_res["matched_technologies"],
            missing_technologies=skill_match_res["missing_technologies"],
            ranked_projects=ranked_projects,
        )
