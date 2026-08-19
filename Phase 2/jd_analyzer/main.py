"""
main.py -- Phase 2 CLI entry point.

Usage:
    python -m phase_2.jd_analyzer.main <path-to-jd-file>

Example:
    python -m phase_2.jd_analyzer.main "Phase 2/input/sample_jd.txt"
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _print_section(title: str, items: list) -> None:
    if items:
        print(f"\n{title}:")
        for item in items:
            print(f"  - {item}")
    else:
        print(f"\n{title}: (none)")


def main() -> int:
    print("\n" + "=" * 60)
    print("  Automatic Job Application System")
    print("  Phase 2 -- JD Analysis Engine")
    print("=" * 60 + "\n")

    if len(sys.argv) < 2:
        print("Usage: python -m phase_2.jd_analyzer.main <path-to-jd-file>")
        print("Example: python -m phase_2.jd_analyzer.main \"Phase 2/input/sample_jd.txt\"")
        return 1

    jd_path = Path(sys.argv[1])

    # -- 1. Read JD --------------------------------------------------------------
    print(f"  Reading JD from: {jd_path}")
    if not jd_path.exists():
        print(f"\n  [ERROR] File not found: {jd_path}")
        return 1

    try:
        jd_text = jd_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"\n  [ERROR] Cannot read file: {exc}")
        return 1

    # -- 2. Validate -------------------------------------------------------------
    print("  Validating input...")
    from phase_2.jd_analyzer.validators import validate_jd_input, JDValidationError
    try:
        jd_text = validate_jd_input(jd_text)
    except JDValidationError as exc:
        print(f"\n  [ERROR] Validation error: {exc}")
        return 1

    # -- 3. Analyze --------------------------------------------------------------
    print("  Analyzing with Gemini...")
    from phase_2.jd_analyzer.jd_analyzer import JDAnalyzer
    from phase_2.jd_analyzer.gemini_client import GeminiConfigError, GeminiAPIError
    try:
        analyzer = JDAnalyzer()
        analysis = analyzer.analyze(jd_text)
    except GeminiConfigError as exc:
        print(f"\n  [ERROR] Gemini configuration error:\n    {exc}")
        return 1
    except GeminiAPIError as exc:
        print(f"\n  [ERROR] Gemini API error:\n    {exc}")
        return 1

    model_used = analyzer.model_name

    # -- 4. Save to Firestore ----------------------------------------------------
    print("  Saving to Firestore...")
    from phase_2.jd_analyzer.firestore_service import save_jd_analysis
    try:
        doc_id = save_jd_analysis(jd_text, analysis, model_used)
    except Exception as exc:  # noqa: BLE001
        print(f"\n  [ERROR] Firestore error:\n    {exc}")
        return 1

    # -- 5. Save local JSON ------------------------------------------------------
    from phase_2.jd_analyzer.config import config
    output_dir = config.OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{doc_id}.json"

    output_data = {
        "document_id": doc_id,
        "model": model_used,
        "analysis": analysis.model_dump(),
    }
    output_path.write_text(
        json.dumps(output_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # -- 6. Display results ------------------------------------------------------
    print("\n" + "-" * 60)
    print("\n  [OK] JD Analysis Successful.\n")
    print(f"  Job Title:        {analysis.job_title or '(not stated)'}")
    print(f"  Company:          {analysis.company or '(not stated)'}")
    print(f"  Role Category:    {analysis.role_category or '(not stated)'}")
    print(f"  Experience Level: {analysis.experience_level or '(not stated)'}")
    print(f"  Employment Type:  {analysis.employment_type or '(not stated)'}")
    print(f"  Location:         {analysis.location or '(not stated)'}")

    _print_section("Required Skills",  analysis.required_skills)
    _print_section("Preferred Skills", analysis.preferred_skills)
    _print_section("Technologies",     analysis.technologies)
    _print_section("Responsibilities", analysis.responsibilities)
    _print_section("Education",        analysis.education_requirements)
    _print_section("Experience",       analysis.experience_requirements)
    _print_section("Keywords",         analysis.keywords)

    print(f"\n  Gemini Model:       {model_used}")
    print(f"  Firestore Document: {config.FIRESTORE_JD_COLLECTION}/{doc_id}")
    print(f"  Local Output:       {output_path}")
    print("\n" + "-" * 60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
