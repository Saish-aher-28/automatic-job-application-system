"""
scorer.py — Scoring math and formulas for Phase 3 Job ↔ Profile Match.

Formulas:
1. Project Final Score:
   - If evaluated semantically:
     final_project_score = (preliminary_score * (1 - blend_weight)) + (semantic_score * blend_weight)
     (where blend_weight is config.PROJECT_SEMANTIC_BLEND_WEIGHT, default 0.70)
   - If not evaluated semantically:
     final_project_score = preliminary_score

2. Overall Match Score:
   overall_score = (required_skill_score * REQUIRED_SKILL_WEIGHT)
                   + (preferred_skill_score * PREFERRED_SKILL_WEIGHT)
                   + (technology_score * TECHNOLOGY_WEIGHT)
                   + (project_relevance_score * PROJECT_WEIGHT)
   (where project_relevance_score is the average of the top 3 ranked projects)
"""

from typing import List
from phase_3.matcher.config import config


def calculate_project_final_score(
    preliminary_score: float,
    semantic_score: float | None,
) -> float:
    """
    Combines Stage 1 preliminary score and Stage 2 semantic score.
    """
    if semantic_score is None:
        return round(preliminary_score, 1)

    blend = config.PROJECT_SEMANTIC_BLEND_WEIGHT
    final_score = (preliminary_score * (1.0 - blend)) + (semantic_score * blend)
    return round(final_score, 1)


def calculate_overall_match_score(
    required_score: float,
    preferred_score: float,
    tech_score: float,
    project_scores: List[float],
) -> float:
    """
    Calculates the final overall job match score.
    Uses configurable weights from config.py.
    The project relevance score is the average of the top 3 projects.
    """
    # 1. Calculate project relevance score as the average of the top 3 projects
    if project_scores:
        sorted_scores = sorted(project_scores, reverse=True)
        top_scores = sorted_scores[:3]  # top 3 projects
        proj_relevance = sum(top_scores) / len(top_scores)
    else:
        proj_relevance = 0.0

    # 2. Weighted sum
    overall = (
        required_score * config.REQUIRED_SKILL_WEIGHT
        + preferred_score * config.PREFERRED_SKILL_WEIGHT
        + tech_score * config.TECHNOLOGY_WEIGHT
        + proj_relevance * config.PROJECT_WEIGHT
    )

    return round(overall, 1)
