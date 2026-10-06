"""
main.py -- Phase 4 CLI entry point for Dynamic Resume Tailoring.

Usage:
    python -m phase_4.resume_tailor.main <match_id>
    python -m phase_4.resume_tailor.main <match_id> --json
    python -m phase_4.resume_tailor.main <match_id> --dry-run

Example:
    python -m phase_4.resume_tailor.main M4QoZgYhNr4oYkXYnYuL
"""

from __future__ import annotations

import json
import logging
import sys

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


BANNER = """
============================================================
  Automatic Job Application System
  Phase 4 -- Dynamic Resume Tailoring
============================================================
"""


def main() -> int:
    print(BANNER)

    if len(sys.argv) < 2:
        print("Usage: python -m phase_4.resume_tailor.main <match_id> [--json] [--dry-run]")
        print("Example: python -m phase_4.resume_tailor.main M4QoZgYhNr4oYkXYnYuL")
        return 1

    match_id  = sys.argv[1]
    print_json = "--json"    in sys.argv
    dry_run    = "--dry-run" in sys.argv

    print(f"  Match ID: {match_id}")
    if dry_run:
        print("  [dry-run mode -- PDF compilation will be skipped]\n")
    print()

    from phase_4.resume_tailor.resume_pipeline import generate_tailored_resume

    try:
        result = generate_tailored_resume(match_id=match_id, dry_run=dry_run)
    except RuntimeError as exc:
        print(f"\n  [ERROR] {exc}")
        return 1
    except Exception as exc:
        print(f"\n  [UNEXPECTED ERROR] {exc}")
        logger.exception("Unexpected error during Phase 4 pipeline.")
        return 1

    # -- Output --------------------------------------------------------------
    if print_json:
        print("\n" + "-" * 60)
        print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
        print("-" * 60 + "\n")
        return 0 if result.generation_status == "success" else 2

    print()
    print("-" * 60)
    print()

    if result.generation_status == "success":
        print("  OK  Tailored Resume Generated.\n")
    elif result.generation_status == "partial":
        print("  WARN  Tailored Resume Generated (with warnings).\n")
    else:
        print("  FAIL  Tailored Resume Generation Failed.\n")

    print(f"  Job:          {result.job_title}")
    print(f"  Match ID:     {result.match_id}")
    print(f"  Resume ID:    {result.resume_id}")

    overall_pct = ""
    try:
        from phase_4.resume_tailor.firestore_service import get_match_result
        raw = get_match_result(match_id)
        scores = raw.get("scores", {}) or {}
        overall = scores.get("overall", None)
        if overall is not None:
            overall_pct = f" ({overall}%)"
    except Exception:
        pass
    print(f"  Match Score:  {overall_pct.strip()}" if overall_pct else "")

    print()
    print("  Selected Projects:")
    for i, name in enumerate(result.selected_project_names, 1):
        print(f"    {i}. {name}")

    if result.emphasized_skills:
        print()
        print(f"  Emphasized Skills:  {', '.join(result.emphasized_skills)}")

    print()
    if result.page_count is not None:
        limit_ok = "OK" if result.page_count <= 2 else "WARN"
        print(f"  Pages:        {limit_ok} {result.page_count} / 2")
    else:
        print("  Pages:        (unknown -- dry-run or compilation skipped)")

    print()
    print(f"  TEX:  {result.tex_path}")
    if result.pdf_path:
        print(f"  PDF:  {result.pdf_path}")

    if result.warnings:
        print()
        print("  Warnings:")
        for w in result.warnings:
            print(f"    WARN  {w}")

    print()
    print("-" * 60)
    print()

    if result.generation_status == "failed":
        return 1
    if result.page_count is not None and result.page_count > 2:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
