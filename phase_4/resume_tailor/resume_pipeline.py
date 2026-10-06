"""
resume_pipeline.py — Phase 4 main orchestrator.

Pipeline:
    1.  Load Phase 3 match result from Firestore
    2.  Parse match result (normalise nested structure)
    3.  Load JD analysis from Firestore
    4.  Load all profile data (profile, skills, projects, education, ...)
    5.  Run project selector  → selected project IDs
    6.  Fetch full project docs
    7.  Run skill selector    → reordered skills_grouped
    8.  Run content tailor    → TailoringPlan (via Gemini or deterministic)
    9.  Apply tailoring plan  (summary + skill order)
   10.  Build resume_data dict (same shape as Phase 1 generate_resume() expects)
   11.  Call Phase 1 render_resume() → tex_content
   12.  Write .tex to tailored output directory (NOT latex/output/)
   13.  Compile PDF via Phase 1 compile_pdf()
   14.  Count pages via Phase 1 count_pdf_pages()
   15.  Overflow remediation loop  (drop lowest project → re-render → recheck)
   16.  Placeholder validation
   17.  Save Firestore record
   18.  Return TailoredResumeResult

Phase 1 files modified: NONE.
Phase 3 job_matches documents: READ ONLY.
Master LaTeX template: READ ONLY.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from pathlib import Path
from typing import List, Optional

from phase_4.resume_tailor.config import config
from phase_4.resume_tailor.schemas import TailoredResumeResult, TailoringPlan
from phase_4.resume_tailor import firestore_service
from phase_4.resume_tailor.project_selector import select_projects, build_projects_by_id_map
from phase_4.resume_tailor.skill_selector import reorder_skills, get_actually_emphasized
from phase_4.resume_tailor.content_tailor import ContentTailor

logger = logging.getLogger(__name__)


# ── Helper: parse the nested Phase 3 Firestore document ─────────────────────

def _parse_match_doc(raw: dict) -> dict:
    """
    Normalise the Phase 3 Firestore document into a flat dict matching
    the JobMatchResult field names used throughout the codebase.

    Phase 3 stores data in a nested structure:
        { "jd_document_id": ..., "job_title": ...,
          "scores": { "overall": ..., "required_skills": ..., ... },
          "skill_match": { "matched_required": [...], ... },
          "ranked_projects": [ {...}, ... ] }
    """
    scores     = raw.get("scores", {}) or {}
    skill_match = raw.get("skill_match", {}) or {}

    return {
        "jd_document_id":              raw.get("jd_document_id", ""),
        "job_title":                   raw.get("job_title", "Untitled Position"),
        "overall_match_score":         scores.get("overall", 0.0),
        "required_skill_match_score":  scores.get("required_skills", 0.0),
        "preferred_skill_match_score": scores.get("preferred_skills", 0.0),
        "technology_match_score":      scores.get("technologies", 0.0),
        "project_relevance_score":     scores.get("projects", 0.0),
        "matched_required_skills":     skill_match.get("matched_required", []) or [],
        "missing_required_skills":     skill_match.get("missing_required", []) or [],
        "matched_preferred_skills":    skill_match.get("matched_preferred", []) or [],
        "missing_preferred_skills":    skill_match.get("missing_preferred", []) or [],
        "matched_technologies":        skill_match.get("matched_technologies", []) or [],
        "missing_technologies":        skill_match.get("missing_technologies", []) or [],
        "ranked_projects":             raw.get("ranked_projects", []) or [],
    }


# ── Helper: tailor the summary text ─────────────────────────────────────────

def _tailor_summary(original_summary: str, summary_focus: List[str]) -> str:
    """
    Produce a tailored summary by emphasising matched skills within the original text.

    Strategy (no free-form AI rewriting):
    - If the original summary already naturally mentions the key skills, return as-is.
    - Otherwise, prepend a focused skill phrase at the start of the summary.

    The result must never contain information not in the original profile.
    """
    if not summary_focus or not original_summary:
        return original_summary

    # Check which focus skills are already mentioned in summary
    summary_lower = original_summary.lower()
    missing_from_summary = [
        s for s in summary_focus
        if s.lower() not in summary_lower
    ]

    if not missing_from_summary:
        # All focus skills already mentioned — no change needed
        return original_summary

    # Add a brief focus phrase before the original summary
    # e.g. "Skilled in Python, AWS and Flask. Results-driven..."
    if len(missing_from_summary) == 1:
        focus_phrase = f"Skilled in {missing_from_summary[0]}."
    else:
        skills_str = ", ".join(missing_from_summary[:-1]) + f" and {missing_from_summary[-1]}"
        focus_phrase = f"Skilled in {skills_str}."

    tailored = f"{focus_phrase} {original_summary}"
    return tailored


# ── Helper: validate no {{PLACEHOLDER}} remains ──────────────────────────────

def _check_placeholders(tex_content: str) -> List[str]:
    """Return list of unfilled {{PLACEHOLDER}} tokens found in tex_content."""
    return re.findall(r"\{\{[A-Z_]+\}\}", tex_content)


# ── Helper: write .tex to tailored output dir ────────────────────────────────

def _write_tailored_tex(tex_content: str, match_id: str) -> Path:
    """Write tex content to the tailored output directory for this match."""
    out_dir = config.tailored_output_dir(match_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    tex_path = config.tailored_tex_path(match_id)
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex_content)
    return tex_path


# ── Main pipeline ────────────────────────────────────────────────────────────

def generate_tailored_resume(
    match_id: str,
    dry_run: bool = False,
    tailor: Optional[ContentTailor] = None,
) -> TailoredResumeResult:
    """
    Full Phase 4 tailored resume generation pipeline.

    Args:
        match_id: Phase 3 Firestore document ID from 'job_matches'.
        dry_run:  If True, creates the tailoring plan but skips compilation.
        tailor:   Optional ContentTailor instance (allows injection for tests).

    Returns:
        TailoredResumeResult with all status information.
    """
    warnings: List[str] = []
    resume_id = str(uuid.uuid4())

    # ── 1. Load Phase 3 match result ──────────────────────────────────────────
    print("  Loading match result...", end=" ", flush=True)
    try:
        raw_match = firestore_service.get_match_result(match_id)
    except ValueError as exc:
        raise RuntimeError(f"Match result not found: {exc}") from exc
    match = _parse_match_doc(raw_match)
    jd_doc_id = match["jd_document_id"]
    job_title  = match["job_title"]
    print("OK")

    # ── 2. Load JD analysis ───────────────────────────────────────────────────
    print("  Loading JD analysis...", end=" ", flush=True)
    try:
        jd_data = firestore_service.get_jd_analysis(jd_doc_id)
    except ValueError as exc:
        raise RuntimeError(f"JD analysis not found: {exc}") from exc
    print("OK")

    # ── 3. Load profile data ──────────────────────────────────────────────────
    print("  Loading profile...", end=" ", flush=True)
    profile = firestore_service.get_profile()
    if not profile:
        raise RuntimeError(
            "User profile not found in Firestore. "
            "Ensure Phase 1 profile data has been seeded."
        )
    print("OK")

    # ── 4. Load all supporting profile data ───────────────────────────────────
    print("  Loading skills...", end=" ", flush=True)
    skills_grouped = firestore_service.get_all_skills_grouped()
    print(f"OK  ({sum(len(v) for v in skills_grouped.values())} skills)")

    print("  Loading all projects...", end=" ", flush=True)
    all_projects = firestore_service.get_all_projects()
    print(f"OK  ({len(all_projects)} projects)")

    print("  Loading education...", end=" ", flush=True)
    education = firestore_service.get_education()
    print(f"OK  ({len(education)} records)")

    print("  Loading experience...", end=" ", flush=True)
    experience = firestore_service.get_experience()
    print(f"OK  ({len(experience)} records)")

    print("  Loading certifications...", end=" ", flush=True)
    certifications = firestore_service.get_certifications()
    print(f"OK  ({len(certifications)} records)")

    print("  Loading languages...", end=" ", flush=True)
    languages = firestore_service.get_languages()
    print(f"OK  ({len(languages)} records)")

    print("  Loading interests...", end=" ", flush=True)
    interests = firestore_service.get_interests()
    print(f"OK  ({len(interests)} records)")

    # ── 5. Build project lookup map ───────────────────────────────────────────
    projects_by_id = build_projects_by_id_map(all_projects)

    # ── 6. Project selection ──────────────────────────────────────────────────
    print("  Selecting projects...", end=" ", flush=True)
    ranked_projects: List[dict] = match.get("ranked_projects", []) or []
    jd_analysis = jd_data.get("analysis", jd_data)
    required_techs = jd_analysis.get("technologies", []) or []

    selected_ids = select_projects(
        ranked_projects=ranked_projects,
        all_projects_by_id=projects_by_id,
        required_technologies=required_techs,
        limit=config.PROJECT_SELECT_LIMIT,
    )

    if not selected_ids:
        warnings.append("No projects were selected for the resume.")
    print(f"OK  ({len(selected_ids)} selected)")

    # ── 7. Fetch full selected project documents ───────────────────────────────
    selected_projects = []
    for pid in selected_ids:
        proj = projects_by_id.get(pid)
        if proj is None:
            # Try fetching directly from Firestore in case map is stale
            proj = firestore_service.get_project_by_id(pid)
        if proj:
            selected_projects.append(proj)
        else:
            warnings.append(f"Project ID '{pid}' selected but not found in Firestore.")

    # ── 8. Content tailoring plan ─────────────────────────────────────────────
    print("  Creating tailoring plan...", end=" ", flush=True)
    ranked_project_ids = [p.get("project_id", "") for p in ranked_projects if p.get("project_id")]

    if tailor is None:
        tailor = ContentTailor()

    tailoring_plan: TailoringPlan = tailor.plan(
        profile=profile,
        jd_data=jd_data,
        match_result=match,
        skills_grouped=skills_grouped,
        ranked_project_ids=ranked_project_ids,
        all_projects_by_id=projects_by_id,
        project_limit=config.PROJECT_SELECT_LIMIT,
    )
    print("OK")

    # ── 9. Apply tailoring plan ────────────────────────────────────────────────
    # Skill reordering
    print("  Reordering skills...", end=" ", flush=True)
    reordered_skills = reorder_skills(skills_grouped, tailoring_plan.skills_to_emphasize)
    actually_emphasized = get_actually_emphasized(skills_grouped, tailoring_plan.skills_to_emphasize)
    print(f"OK  ({len(actually_emphasized)} skills emphasised)")

    # Summary tailoring
    original_summary = profile.get("summary", "")
    tailored_summary = _tailor_summary(original_summary, tailoring_plan.summary_focus)
    if tailored_summary != original_summary:
        logger.info("Summary tailored to emphasise: %s", tailoring_plan.summary_focus)

    # Build a tailored profile dict (never modifies the Firestore profile)
    tailored_profile = dict(profile)
    tailored_profile["summary"] = tailored_summary

    # ── 10. Build resume_data dict (Phase 1 format) ───────────────────────────
    print("  Preparing resume data...", end=" ", flush=True)
    resume_data = {
        "profile":        tailored_profile,
        "projects":       selected_projects,
        "skills":         reordered_skills,
        "education":      education,
        "experience":     experience,
        "certifications": certifications,
        "languages":      languages,
        "interests":      interests,
    }
    print("OK")

    # ── 11. Render LaTeX (Phase 1 renderer, unchanged) ────────────────────────
    print("  Rendering LaTeX...", end=" ", flush=True)
    from resume_engine.latex_renderer import render_resume
    try:
        tex_content = render_resume(resume_data)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Master LaTeX template not found: {exc}") from exc
    print("OK")

    # ── 12. Placeholder validation ─────────────────────────────────────────────
    remaining_placeholders = _check_placeholders(tex_content)
    if remaining_placeholders:
        raise RuntimeError(
            f"Unresolved placeholders in generated LaTeX: {set(remaining_placeholders)}\n"
            "Generation aborted to prevent corrupt PDF."
        )

    # ── 13. Write .tex ─────────────────────────────────────────────────────────
    print("  Writing .tex file...", end=" ", flush=True)
    tex_path = _write_tailored_tex(tex_content, match_id)
    print(f"OK  {tex_path}")

    if dry_run:
        print("  [dry-run] Skipping PDF compilation.")
        return TailoredResumeResult(
            resume_id=resume_id,
            match_id=match_id,
            jd_document_id=jd_doc_id,
            job_title=job_title,
            selected_project_ids=selected_ids,
            selected_project_names=[p.get("name", "") for p in selected_projects],
            emphasized_skills=actually_emphasized,
            page_count=None,
            tex_path=str(tex_path),
            pdf_path=None,
            generation_status="partial",
            warnings=warnings + ["dry-run: PDF compilation skipped."],
        )

    # ── 14-15. Compile PDF + overflow remediation ──────────────────────────────
    print("  Compiling PDF...")
    from resume_engine.resume_generator import compile_pdf, count_pdf_pages

    current_projects = list(selected_projects)
    current_selected_ids = list(selected_ids)
    pdf_path: Optional[Path] = None
    page_count: Optional[int] = None
    generation_status = "failed"

    for iteration in range(config.MAX_OVERFLOW_RETRIES + 1):
        if iteration > 0:
            # Re-render with reduced project count (drop lowest-scored project)
            print(f"  WARN: Page overflow -- dropping 1 project (iteration {iteration})...")
            current_projects = current_projects[:-1]
            current_selected_ids = current_selected_ids[:-1]
            if not current_projects:
                warnings.append("No projects remain after overflow reduction.")
                generation_status = "partial"
                break

            resume_data["projects"] = current_projects
            try:
                tex_content = render_resume(resume_data)
            except Exception as exc:
                warnings.append(f"Re-render failed: {exc}")
                break

            remaining_placeholders = _check_placeholders(tex_content)
            if remaining_placeholders:
                warnings.append(f"Unresolved placeholders after re-render: {set(remaining_placeholders)}")
                break

            tex_path = _write_tailored_tex(tex_content, match_id)

        pdf_ok, compiled_pdf, pdf_msg = compile_pdf(tex_path)
        print(f"  {pdf_msg}")

        if not pdf_ok or compiled_pdf is None:
            warnings.append(f"PDF compilation failed: {pdf_msg}")
            break

        pdf_path = compiled_pdf
        page_count = count_pdf_pages(pdf_path)

        if page_count is not None and page_count <= config.MAX_RESUME_PAGES:
            generation_status = "success"
            break

        if page_count is not None and page_count > config.MAX_RESUME_PAGES:
            if iteration >= config.MAX_OVERFLOW_RETRIES:
                warnings.append(
                    f"Resume is {page_count} pages after {config.MAX_OVERFLOW_RETRIES} "
                    f"overflow reduction attempts. Consider lowering RESUME_PROJECT_LIMIT."
                )
                generation_status = "partial"
                # Still keep the partially-compliant PDF
                break
        else:
            # page_count is None — treat as success with warning
            generation_status = "success"
            warnings.append("Could not determine PDF page count (PyMuPDF unavailable).")
            break

    # ── 16. Save Firestore record ──────────────────────────────────────────────
    print("  Saving output to Firestore...", end=" ", flush=True)
    tailored_meta = {
        "resume_id":             resume_id,
        "match_id":              match_id,
        "jd_document_id":        jd_doc_id,
        "job_title":             job_title,
        "generator_version":     config.GENERATOR_VERSION,
        "selected_projects":     [p.get("name", "") for p in current_projects],
        "selected_project_ids":  current_selected_ids,
        "emphasized_skills":     actually_emphasized,
        "tailoring_summary": (
            f"summary_tailored: {tailored_summary != original_summary}, "
            f"skills_reordered: {bool(actually_emphasized)}, "
            f"projects_selected: {[p.get('name', '') for p in current_projects]}"
        ),
        "page_count":            page_count,
        "generation_status":     generation_status,
        "tex_path":              str(tex_path),
        "pdf_path":              str(pdf_path) if pdf_path else None,
        "warnings":              warnings,
    }

    try:
        saved_id = firestore_service.save_tailored_resume(tailored_meta)
        print(f"OK  (resume_id: {saved_id})")
    except Exception as exc:
        warnings.append(f"Firestore save failed: {exc}")
        print(f"WARN: Firestore save failed: {exc}")
        saved_id = resume_id  # use local UUID as fallback

    return TailoredResumeResult(
        resume_id=saved_id,
        match_id=match_id,
        jd_document_id=jd_doc_id,
        job_title=job_title,
        selected_project_ids=current_selected_ids,
        selected_project_names=[p.get("name", "") for p in current_projects],
        emphasized_skills=actually_emphasized,
        page_count=page_count,
        tex_path=str(tex_path),
        pdf_path=str(pdf_path) if pdf_path else None,
        generation_status=generation_status,
        warnings=warnings,
    )
