"""
skill_matcher.py — Deterministic skill and technology matching.
"""

from typing import List, Tuple
from phase_3.matcher.normalization import normalize_skill_name, normalize_skill_list


def calculate_match_details(
    jd_items: List[str],
    user_items: List[str],
) -> Tuple[List[str], List[str], float]:
    """
    Compares a list of JD requirements against a list of user skills/tech.
    Performs case-insensitive matching.

    Returns:
        Tuple: (matched_items, missing_items, match_score_percentage)
    """
    # Normalize JD items
    norm_jd_list = normalize_skill_list(jd_items)
    if not norm_jd_list:
        return [], [], 100.0

    # Normalize user items and keep case-insensitive lookup
    norm_user_list = normalize_skill_list(user_items)
    user_lookup = {u.lower(): u for u in norm_user_list}

    matched = []
    missing = []

    for jd_item in norm_jd_list:
        jd_item_lower = jd_item.lower()
        if jd_item_lower in user_lookup:
            # Match found! Use user's original/canonical capitalization
            matched.append(user_lookup[jd_item_lower])
        else:
            missing.append(jd_item)

    score = (len(matched) / len(norm_jd_list)) * 100.0
    return matched, missing, round(score, 1)


def match_skills_and_technologies(
    jd_required: List[str],
    jd_preferred: List[str],
    jd_technologies: List[str],
    user_skills: List[str],
    user_project_technologies: List[str],
) -> dict:
    """
    Match required skills, preferred skills, and technologies.
    Technologies compare JD technologies against BOTH user skills AND project technologies.

    Returns dict containing matched lists, missing lists, and scores.
    """
    # Required skills match (profile skills only)
    matched_req, missing_req, req_score = calculate_match_details(
        jd_required, user_skills
    )

    # Preferred skills match (profile skills only)
    matched_pref, missing_pref, pref_score = calculate_match_details(
        jd_preferred, user_skills
    )

    # Technologies match (profile skills + project technologies)
    combined_user_tech = list(set(user_skills + user_project_technologies))
    matched_tech, missing_tech, tech_score = calculate_match_details(
        jd_technologies, combined_user_tech
    )

    return {
        "matched_required_skills":  matched_req,
        "missing_required_skills":  missing_req,
        "required_skill_match_score": req_score,

        "matched_preferred_skills":   matched_pref,
        "missing_preferred_skills":   missing_pref,
        "preferred_skill_match_score": pref_score,

        "matched_technologies":       matched_tech,
        "missing_technologies":       missing_tech,
        "technology_match_score":     tech_score,
    }
