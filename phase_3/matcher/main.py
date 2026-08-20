"""
main.py -- Phase 3 CLI entry point for JD ↔ User Profile Matching.

Usage:
    python -m phase_3.matcher.main <jd_document_id> [--json]

Example:
    python -m phase_3.matcher.main zLDQD4N1XPJjDpGDjcHj
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Configure clean console logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _print_list(title: str, items: list) -> None:
    if items:
        print(f"\n{title}:")
        for item in items:
            print(f"  - {item}")
    else:
        print(f"\n{title}: (none)")


def main() -> int:
    print("\n" + "=" * 60)
    print("  Automatic Job Application System")
    print("  Phase 3 -- JD <-> User Profile Matching Engine")
    print("=" * 60 + "\n")

    if len(sys.argv) < 2:
        print("Usage: python -m phase_3.matcher.main <jd_document_id> [--json]")
        print("Example: python -m phase_3.matcher.main zLDQD4N1XPJjDpGDjcHj")
        return 1

    jd_doc_id = sys.argv[1]
    print_json = "--json" in sys.argv

    # ── 1. Retrieve data from Firestore ──
    print(f"  Retrieving Job Description '{jd_doc_id}' from Firestore...")
    from phase_3.matcher.firestore_service import (
        get_jd_analysis,
        get_user_profile,
        get_user_skills,
        get_user_projects,
        save_match_result,
    )

    try:
        jd_data = get_jd_analysis(jd_doc_id)
    except Exception as exc:
        print(f"\n  [ERROR] Failed to fetch JD document: {exc}")
        return 1

    print("  Loading user profile data from Firestore...")
    try:
        profile_data = get_user_profile()
        skills = get_user_skills()
        projects = get_user_projects()
    except Exception as exc:
        print(f"\n  [ERROR] Failed to fetch user profile data: {exc}")
        return 1

    print(f"  Loaded Profile, {len(skills)} skills, and {len(projects)} projects.")

    # ── 2. Run Matching Orchestrator ──
    print("  Evaluating matches and running semantic project evaluation...")
    from phase_3.matcher.matcher import JDProfileMatcher
    try:
        matcher = JDProfileMatcher()
        match_result = matcher.match(
            jd_document_id=jd_doc_id,
            jd_data=jd_data,
            profile_data=profile_data,
            skills=skills,
            projects=projects,
        )
    except Exception as exc:
        print(f"\n  [ERROR] Matching failed: {exc}")
        return 1

    # ── 3. Save Match Result to Firestore ──
    print("  Saving match result to Firestore...")
    try:
        match_id = save_match_result(match_result)
    except Exception as exc:
        print(f"\n  [ERROR] Failed to save result to Firestore: {exc}")
        return 1

    # ── 4. Save Local JSON Output ──
    from phase_3.matcher.config import config
    output_dir = config.OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{match_id}.json"

    try:
        output_path.write_text(
            json.dumps(match_result.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"\n  [WARNING] Failed to write local JSON output: {exc}")

    # ── 5. Output Result ──
    if print_json:
        print("\n" + "-" * 60)
        print(json.dumps(match_result.model_dump(), indent=2, ensure_ascii=False))
        print("-" * 60 + "\n")
        return 0

    print("\n" + "-" * 60)
    print("\n  [OK] Job Match Analysis Complete.\n")
    print(f"  Job Title:           {match_result.job_title}")
    print(f"  Overall Match Score: {match_result.overall_match_score}%")
    print(f"  Required Skills:     {match_result.required_skill_match_score}%")
    print(f"  Preferred Skills:    {match_result.preferred_skill_match_score}%")
    print(f"  Technologies:        {match_result.technology_match_score}%")
    print(f"  Project Relevance:   {match_result.project_relevance_score}% (average of top 3)")

    _print_list("Matched Required Skills", match_result.matched_required_skills)
    _print_list("Missing Required Skills", match_result.missing_required_skills)
    _print_list("Matched Preferred Skills", match_result.matched_preferred_skills)
    _print_list("Missing Preferred Skills", match_result.missing_preferred_skills)

    print("\nRanked Projects:")
    for idx, p in enumerate(match_result.ranked_projects, 1):
        sem_str = f" [Semantic: {p.semantic_score}%]" if p.semantic_score is not None else ""
        print(f"  {idx}. {p.project_name} -- Score: {p.final_project_score}% (Prelim: {p.preliminary_score}%{sem_str})")
        print(f"     Reason: {p.reason}")

    print(f"\n  Firestore Match ID: {config.FIRESTORE_MATCH_COLLECTION}/{match_id}")
    print(f"  Local JSON Output:  {output_path}")
    print("\n" + "-" * 60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
