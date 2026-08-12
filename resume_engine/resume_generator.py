"""
resume_generator.py — Orchestrates the full resume generation pipeline.

Pipeline:
    1. Load profile from Firestore
    2. Load projects (filtered + limited for resume)
    3. Load skills (grouped by category)
    4. Load education
    5. Load experience
    6. Load certifications
    7. Load languages
    8. Load interests
    9. Validate all loaded data
   10. Render LaTeX using latex_renderer
   11. Write .tex to output directory
   12. Compile PDF (if pdflatex available)
   13. Validate page count
   14. Return a result summary

The LaTeX renderer does NOT query Firestore — all data is passed to it.
"""

import subprocess
import shutil
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from resume_engine.config import config
from resume_engine.profile_service import get_profile
from resume_engine.project_service import get_all_projects, get_projects_for_resume
from resume_engine.skill_service import get_skills_by_category
from resume_engine.education_service import get_all_education
from resume_engine.experience_service import get_all_experience
from resume_engine.certification_service import get_all_certifications
from resume_engine.language_service import get_all_languages
from resume_engine.interest_service import get_all_interests
from resume_engine.latex_renderer import render_resume, write_tex
from resume_engine.validators import validate_profile


@dataclass
class GenerationResult:
    """Result of a resume generation run."""
    success: bool
    tex_path: Optional[Path] = None
    pdf_path: Optional[Path] = None
    page_count: Optional[int] = None
    page_limit_ok: Optional[bool] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def count_pdf_pages(pdf_path: Path) -> Optional[int]:
    """
    Count the number of pages in a PDF file using PyMuPDF.

    Returns:
        Page count, or None if counting fails.
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        count = doc.page_count
        doc.close()
        return count
    except Exception as e:
        print(f"  ⚠  Could not count PDF pages: {e}")
        return None


def compile_pdf(tex_path: Path) -> tuple[bool, Optional[Path], str]:
    """
    Compile a .tex file to PDF using pdflatex.

    Runs pdflatex twice for stable cross-references.

    Returns:
        (success: bool, pdf_path: Path|None, message: str)
    """
    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        msg = (
            "\n"
            "  ✗  pdflatex not found. The .tex file was generated successfully,\n"
            "     but PDF compilation requires a LaTeX distribution.\n"
            "\n"
            "  To install LaTeX on Windows:\n"
            "    Option 1 (Recommended): MiKTeX\n"
            "      → https://miktex.org/download\n"
            "      → Download and run the installer\n"
            "      → Restart your terminal after installation\n"
            "\n"
            "    Option 2: TeX Live\n"
            "      → https://tug.org/texlive/\n"
            "\n"
            "  After installing, run:  python -m resume_engine.main\n"
        )
        return False, None, msg

    output_dir = tex_path.parent
    tex_name   = tex_path.name

    try:
        for run in range(2):  # Two passes for stable references
            result = subprocess.run(
                [
                    pdflatex,
                    "-interaction=nonstopmode",
                    "-output-directory", str(output_dir),
                    str(tex_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                # Try to find the error line in pdflatex output
                error_lines = [
                    line for line in result.stdout.splitlines()
                    if line.startswith("!") or "Error" in line
                ]
                error_summary = "\n".join(error_lines[:5]) if error_lines else result.stdout[-500:]
                return False, None, f"pdflatex failed:\n{error_summary}"

        pdf_path = output_dir / tex_name.replace(".tex", ".pdf")
        if not pdf_path.exists():
            return False, None, "pdflatex ran but PDF file was not created."

        return True, pdf_path, "PDF compiled successfully."

    except subprocess.TimeoutExpired:
        return False, None, "pdflatex timed out after 60 seconds."
    except Exception as e:
        return False, None, f"Unexpected error during PDF compilation: {e}"


def generate_resume(project_limit: Optional[int] = None) -> GenerationResult:
    """
    Full resume generation pipeline.

    Args:
        project_limit: Override RESUME_PROJECT_LIMIT for this run.

    Returns:
        GenerationResult with all status information.
    """
    result = GenerationResult(success=False)
    limit  = project_limit if project_limit is not None else config.RESUME_PROJECT_LIMIT

    # ── Step 1: Load profile ─────────────────────────────────────────
    print("  Loading profile...", end=" ", flush=True)
    profile = get_profile()
    if not profile:
        result.errors.append(
            "Profile not found in Firestore. "
            "Run 'python scripts/seed_profile.py' first."
        )
        return result

    profile_errors = validate_profile(profile)
    if profile_errors:
        for e in profile_errors:
            result.warnings.append(e)

    print("✓")

    # ── Step 2: Load projects ────────────────────────────────────────
    print("  Loading projects...", end=" ", flush=True)
    all_projects = get_all_projects()
    resume_projects = get_projects_for_resume(limit)
    print(f"✓  ({len(resume_projects)}/{len(all_projects)} selected for resume, limit={limit})")
    result.stats["projects_total"]  = len(all_projects)
    result.stats["projects_resume"] = len(resume_projects)

    # ── Step 3: Load skills ──────────────────────────────────────────
    print("  Loading skills...", end=" ", flush=True)
    skills_grouped = get_skills_by_category()
    total_skills   = sum(len(v) for v in skills_grouped.values())
    print(f"✓  ({total_skills} skills in {len(skills_grouped)} categories)")
    result.stats["skills"] = total_skills

    # ── Step 4: Load education ───────────────────────────────────────
    print("  Loading education...", end=" ", flush=True)
    education = get_all_education()
    print(f"✓  ({len(education)} records)")
    result.stats["education"] = len(education)

    # ── Step 5: Load experience ──────────────────────────────────────
    print("  Loading experience...", end=" ", flush=True)
    experience = get_all_experience()
    print(f"✓  ({len(experience)} records)")
    result.stats["experience"] = len(experience)

    # ── Step 6: Load certifications ──────────────────────────────────
    print("  Loading certifications...", end=" ", flush=True)
    certifications = get_all_certifications()
    print(f"✓  ({len(certifications)} records)")
    result.stats["certifications"] = len(certifications)

    # ── Step 7: Load languages ───────────────────────────────────────
    print("  Loading languages...", end=" ", flush=True)
    languages = get_all_languages()
    print(f"✓  ({len(languages)} records)")
    result.stats["languages"] = len(languages)

    # ── Step 8: Load interests ───────────────────────────────────────
    print("  Loading interests...", end=" ", flush=True)
    interests = get_all_interests()
    print(f"✓  ({len(interests)} records)")
    result.stats["interests"] = len(interests)

    # ── Step 9: Build resume data bundle ─────────────────────────────
    resume_data = {
        "profile":        profile,
        "projects":       resume_projects,
        "skills":         skills_grouped,
        "education":      education,
        "experience":     experience,
        "certifications": certifications,
        "languages":      languages,
        "interests":      interests,
    }

    # ── Step 10: Render LaTeX ────────────────────────────────────────
    print("  Rendering LaTeX...", end=" ", flush=True)
    try:
        tex_content = render_resume(resume_data)
    except FileNotFoundError as e:
        result.errors.append(str(e))
        return result
    print("✓")

    # ── Step 11: Write .tex ──────────────────────────────────────────
    print("  Writing .tex file...", end=" ", flush=True)
    tex_path = write_tex(tex_content)
    result.tex_path = tex_path
    print(f"✓  {tex_path}")

    # ── Step 12: Compile PDF ─────────────────────────────────────────
    print("  Compiling PDF...")
    pdf_ok, pdf_path, pdf_msg = compile_pdf(tex_path)
    print(f"  {pdf_msg}")

    if pdf_ok and pdf_path:
        result.pdf_path = pdf_path

        # ── Step 13: Validate page count ─────────────────────────────
        print("  Counting pages...", end=" ", flush=True)
        pages = count_pdf_pages(pdf_path)
        result.page_count = pages

        if pages is not None:
            if pages <= config.MAX_RESUME_PAGES:
                result.page_limit_ok = True
                print(f"✓  {pages} page(s) — within {config.MAX_RESUME_PAGES}-page limit.")
            else:
                result.page_limit_ok = False
                msg = (
                    f"Resume is {pages} pages — exceeds the {config.MAX_RESUME_PAGES}-page limit.\n"
                    f"  Suggestion: lower RESUME_PROJECT_LIMIT (currently {limit}) in your .env file.\n"
                    f"  Projects in Firestore remain untouched."
                )
                result.warnings.append(msg)
                print(f"⚠  {msg}")
        else:
            print("  (Could not determine page count)")

    result.success = True
    return result
