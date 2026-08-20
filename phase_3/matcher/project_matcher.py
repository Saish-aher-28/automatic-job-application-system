"""
project_matcher.py — Stage 1 deterministic preliminary scoring for user projects.
"""

from typing import Dict, List, Set
from phase_3.matcher.config import config
from phase_3.matcher.normalization import normalize_skill_name, normalize_skill_list


def _matches_project(
    jd_item: str,
    project_techs_norm: Set[str],
    project_kws_norm: Set[str],
    project_text_lower: str,
) -> bool:
    """
    Checks if a normalized JD requirement is present in the project details.
    Matches if found in normalized technologies, keywords, or as a substring in
    the project description/bullets.
    """
    jd_item_lower = jd_item.lower()
    if jd_item_lower in project_techs_norm:
        return True
    if jd_item_lower in project_kws_norm:
        return True
    # Substring search in text (e.g. for "REST API" or multi-word terms)
    if jd_item_lower in project_text_lower:
        return True
    return False


def calculate_project_preliminary_score(
    project: dict,
    jd_required: List[str],
    jd_preferred: List[str],
    jd_technologies: List[str],
    jd_keywords: List[str],
    jd_role_category: str | None,
) -> Dict[str, any]:
    """
    Calculates the Stage 1 deterministic preliminary score for a single project.

    Weights are imported from config:
      - PROJECT_REQUIRED_WEIGHT (40%)
      - PROJECT_PREFERRED_WEIGHT (15%)
      - PROJECT_TECHNOLOGY_WEIGHT (20%)
      - PROJECT_KEYWORD_WEIGHT (15%)
      - PROJECT_CATEGORY_WEIGHT (10%)

    Returns:
        Dict containing scores, matched lists, and missing lists.
    """
    # ── 1. Extract and normalize project content ──
    proj_techs = project.get("technologies", [])
    proj_kws   = project.get("keywords", []) or []
    proj_cats  = project.get("categories", []) or []
    proj_desc  = project.get("description", "") or ""
    proj_blts  = project.get("resume_bullets", []) or []

    # Normalized lookup sets
    proj_techs_norm = {t.lower() for t in normalize_skill_list(proj_techs)}
    proj_kws_norm   = {k.lower() for k in normalize_skill_list(proj_kws + proj_cats)}

    # Concatenate textual fields for substring search
    project_text = f"{proj_desc} " + " ".join(proj_blts)
    project_text_lower = project_text.lower()

    # ── 2. Match Required Skills (40% weight) ──
    norm_required = normalize_skill_list(jd_required)
    matched_req = []
    missing_req = []
    if norm_required:
        for r in norm_required:
            if _matches_project(r, proj_techs_norm, proj_kws_norm, project_text_lower):
                matched_req.append(r)
            else:
                missing_req.append(r)
        req_score = (len(matched_req) / len(norm_required)) * 100.0
    else:
        req_score = 100.0

    # ── 3. Match Preferred Skills (15% weight) ──
    norm_preferred = normalize_skill_list(jd_preferred)
    matched_pref = []
    missing_pref = []
    if norm_preferred:
        for p in norm_preferred:
            if _matches_project(p, proj_techs_norm, proj_kws_norm, project_text_lower):
                matched_pref.append(p)
            else:
                missing_pref.append(p)
        pref_score = (len(matched_pref) / len(norm_preferred)) * 100.0
    else:
        pref_score = 100.0

    # ── 4. Match Technologies (20% weight) ──
    norm_tech = normalize_skill_list(jd_technologies)
    matched_tech = []
    missing_tech = []
    if norm_tech:
        for t in norm_tech:
            if _matches_project(t, proj_techs_norm, proj_kws_norm, project_text_lower):
                matched_tech.append(t)
            else:
                missing_tech.append(t)
        tech_score = (len(matched_tech) / len(norm_tech)) * 100.0
    else:
        tech_score = 100.0

    # ── 5. Match Keywords (15% weight) ──
    norm_kws = normalize_skill_list(jd_keywords)
    matched_kw = []
    if norm_kws:
        for k in norm_kws:
            if _matches_project(k, proj_techs_norm, proj_kws_norm, project_text_lower):
                matched_kw.append(k)
        kw_score = (len(matched_kw) / len(norm_kws)) * 100.0
    else:
        kw_score = 100.0

    # ── 6. Match Role Category (10% weight) ──
    category_score = 0.0
    if jd_role_category:
        jd_cat_lower = jd_role_category.lower().strip()
        if (
            jd_cat_lower in proj_kws_norm
            or jd_cat_lower in proj_techs_norm
            or jd_cat_lower in project_text_lower
        ):
            category_score = 100.0
    else:
        category_score = 100.0

    # ── 7. Calculate Weighted Preliminary Score ──
    prelim_score = (
        req_score * config.PROJECT_REQUIRED_WEIGHT
        + pref_score * config.PROJECT_PREFERRED_WEIGHT
        + tech_score * config.PROJECT_TECHNOLOGY_WEIGHT
        + kw_score * config.PROJECT_KEYWORD_WEIGHT
        + category_score * config.PROJECT_CATEGORY_WEIGHT
    )

    # Union of all matched/missing relevant items
    all_matched_skills = sorted(list(set(matched_req + matched_pref)))
    all_missing_skills = sorted(list(set(missing_req + missing_pref)))

    return {
        "preliminary_score":       round(prelim_score, 1),
        "matched_skills":          all_matched_skills,
        "matched_technologies":    sorted(list(set(matched_tech))),
        "missing_relevant_skills": all_missing_skills,
    }
