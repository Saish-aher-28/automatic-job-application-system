"""
main.py — Entry point for Phase 1 resume generation.

Usage:
    python -m resume_engine.main
    python -m resume_engine.main --limit 4

This connects to Firestore, loads all resume data, generates the .tex,
compiles the PDF (if pdflatex is installed), and reports the result.
"""

import sys
import argparse
from pathlib import Path

from resume_engine.config import config
from resume_engine.resume_generator import generate_resume


BANNER = """
╔══════════════════════════════════════════════════════════╗
║          Automatic Job Application System                ║
║          Phase 1 — Resume Generator                      ║
╚══════════════════════════════════════════════════════════╝
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate resume from Firestore data using the existing LaTeX template."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            f"Override RESUME_PROJECT_LIMIT for this run "
            f"(default: {config.RESUME_PROJECT_LIMIT} from .env)"
        ),
    )
    args = parser.parse_args()

    print(BANNER)

    # ── Configuration warnings ────────────────────────────────────────
    warnings = config.validate()
    if warnings:
        print("  ⚠  Configuration warnings:")
        for w in warnings:
            print(f"     - {w}")
        print()

    # ── Connect to Firestore ──────────────────────────────────────────
    print("  Connecting to Firestore...")
    try:
        from resume_engine.firebase_client import get_firestore_client
        get_firestore_client()
        print("  ✓  Connected.\n")
    except RuntimeError as e:
        print(str(e))
        sys.exit(1)

    # ── Generate ──────────────────────────────────────────────────────
    print("  Generating resume...\n")
    result = generate_resume(project_limit=args.limit)

    # ── Report ────────────────────────────────────────────────────────
    print()
    print("─" * 60)

    if result.errors:
        print("\n  ✗  Generation failed:")
        for err in result.errors:
            print(f"     {err}")
        sys.exit(1)

    if result.warnings:
        print("\n  ⚠  Warnings:")
        for w in result.warnings:
            print(f"     {w}")

    print()
    if result.success:
        print("  ✓  Resume generation successful.")
        print()
        print("  Output:")
        if result.tex_path:
            print(f"    .tex → {result.tex_path}")
        if result.pdf_path:
            print(f"    .pdf → {result.pdf_path}")
        if result.page_count is not None:
            status = "✓" if result.page_limit_ok else "⚠"
            print(f"    {status} Pages: {result.page_count} / {config.MAX_RESUME_PAGES} max")

        print()
        print("  Firestore stats:")
        for key, val in result.stats.items():
            print(f"    {key}: {val}")

    print()

    if result.page_limit_ok is False:
        sys.exit(2)  # Non-zero exit to indicate page limit exceeded


if __name__ == "__main__":
    main()
