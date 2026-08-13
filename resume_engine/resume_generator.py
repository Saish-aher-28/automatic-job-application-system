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
   12. Compile PDF (if tectonic or pdflatex available)
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
        import pymupdf as fitz  # PyMuPDF (replaces deprecated `import fitz`)
        doc = fitz.open(str(pdf_path))
        count = doc.page_count
        doc.close()
        return count
    except Exception as e:
        print(f"  ⚠  Could not count PDF pages: {e}")
        return None


def _detect_latex_engine() -> tuple:
    """
    Detect the best available LaTeX engine.

    Priority:
      1. tectonic  -- lightweight, auto-downloads packages on first use
      2. pdflatex  -- traditional (MiKTeX / TeX Live)

    Returns:
        (engine_name, executable_path) or (None, None)
    """
    # tectonic.exe may be sitting in the project root if installed via the
    # drop-ps1 script rather than added to PATH
    local_tectonic = Path(__file__).resolve().parent.parent / "tectonic.exe"

    for name, candidates in [
        ("tectonic", ["tectonic", str(local_tectonic)]),
        ("pdflatex", ["pdflatex"]),
    ]:
        for candidate in candidates:
            found = shutil.which(candidate)
            if found:
                return name, found
            if Path(candidate).exists():
                return name, candidate

    return None, None


def compile_pdf(tex_path: Path) -> tuple:
    """
    Compile a .tex file to PDF using the best available LaTeX engine.

    Engine priority:
      1. Tectonic  -- single pass, auto-downloads needed packages
      2. pdflatex  -- double pass (MiKTeX / TeX Live)

    Returns:
        (success: bool, pdf_path: Path|None, message: str)
    """
    engine_name, engine_exe = _detect_latex_engine()

    if engine_name is None:
        msg = (
            "\n"
            "  No LaTeX engine found. The .tex was generated successfully,\n"
            "  but PDF compilation requires a LaTeX engine.\n"
            "\n"
            "  Recommended (lightweight): Tectonic\n"
            "    PowerShell:\n"
            "      iex ((New-Object System.Net.WebClient).DownloadString('https://drop-ps1.fullyjustified.net'))\n"
            "    Or: https://github.com/tectonic-typesetting/tectonic/releases\n"
            "\n"
            "  Alternative (full): MiKTeX -- https://miktex.org/download\n"
            "\n"
            "  After installing, run:  python -m resume_engine.main\n"
        )
        return False, None, msg

    output_dir = tex_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if engine_name == "tectonic":
            # Single pass; tectonic downloads missing packages automatically.
            # Allow extra time on first run for package downloads.
            result = subprocess.run(
                [
                    engine_exe,
                    "--outdir", str(output_dir),
                    "--keep-logs",
                    str(tex_path),
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )
            compiler_label = "Tectonic"
        else:
            # pdflatex: two passes for stable cross-references.
            for _ in range(2):
                result = subprocess.run(
                    [
                        engine_exe,
                        "-interaction=nonstopmode",
                        "-output-directory", str(output_dir),
                        str(tex_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            compiler_label = "pdflatex"

        if result.returncode != 0:
            stderr = result.stderr or ""
            stdout = result.stdout or ""
            combined = stdout + "\n" + stderr
            error_lines = [
                line for line in combined.splitlines()
                if line.startswith("!") or "error" in line.lower()
            ]
            error_summary = "\n".join(error_lines[:8]) if error_lines else combined[-600:]
            return False, None, f"{compiler_label} failed:\n{error_summary}"

        pdf_path = output_dir / (tex_path.stem + ".pdf")
        if not pdf_path.exists():
            return False, None, f"{compiler_label} ran but PDF was not created at {pdf_path}"

        return True, pdf_path, f"PDF compiled successfully with {compiler_label}."

    except subprocess.TimeoutExpired:
        return False, None, (
            f"{engine_name} timed out. "
            "On first Tectonic run, package downloads may take a few minutes -- try again."
        )
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
