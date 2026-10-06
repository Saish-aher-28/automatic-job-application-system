"""
skill_selector.py — Reorders existing skills within their categories for JD relevance.

Rules:
  - ONLY reorders skills already present in the user's actual profile.
  - NEVER adds new skills, invents skills, or creates new categories.
  - NEVER removes skills.
  - Skills to emphasize are moved to the front of their category.
  - All other skills follow in their original order.
"""

from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger(__name__)


def reorder_skills(
    skills_grouped: dict[str, list[str]],
    skills_to_emphasize: List[str],
) -> dict[str, list[str]]:
    """
    Reorder skills within each category so that JD-relevant skills appear first.

    Args:
        skills_grouped: Category → ordered list of skill names (from Firestore).
        skills_to_emphasize: Skill names to move to the front of their category.
                             MUST be a strict subset of existing profile skills.

    Returns:
        A new dict with the same categories and skills, but with emphasized
        skills moved to the front of their respective category.
    """
    if not skills_to_emphasize:
        return dict(skills_grouped)

    # Normalize for case-insensitive matching
    emphasize_norm = {s.strip().lower(): s for s in skills_to_emphasize if s.strip()}

    reordered: dict[str, list[str]] = {}

    for category, skill_list in skills_grouped.items():
        if not skill_list:
            reordered[category] = []
            continue

        # Split into emphasized (in JD order) and rest (original order)
        emphasized = []
        rest = []
        matched_norms = set()

        for skill in skill_list:
            skill_norm = skill.strip().lower()
            if skill_norm in emphasize_norm:
                emphasized.append(skill)
                matched_norms.add(skill_norm)
            else:
                rest.append(skill)

        reordered[category] = emphasized + rest

    # Log which skills were actually found and emphasized
    all_skills_flat = [s for lst in skills_grouped.values() for s in lst]
    all_skills_norm = {s.strip().lower() for s in all_skills_flat}

    not_found = [
        orig for norm, orig in emphasize_norm.items()
        if norm not in all_skills_norm
    ]
    if not_found:
        logger.warning(
            "Skills requested for emphasis not found in profile (will be ignored): %s",
            not_found,
        )

    found_count = len(emphasize_norm) - len(not_found)
    logger.info(
        "Skill reorder: %d/%d requested skills emphasized across categories.",
        found_count,
        len(emphasize_norm),
    )

    return reordered


def get_actually_emphasized(
    skills_grouped: dict[str, list[str]],
    skills_to_emphasize: List[str],
) -> List[str]:
    """
    Return only the subset of skills_to_emphasize that actually exist in the profile.
    Used for metadata / Firestore storage.
    """
    all_skills_norm = {
        s.strip().lower()
        for lst in skills_grouped.values()
        for s in lst
    }
    return [s for s in skills_to_emphasize if s.strip().lower() in all_skills_norm]
