"""
latex_renderer.py — Reads the master LaTeX template and produces a filled .tex file.

CRITICAL RULES:
  1. The master template (latex/resume_tex.tex) is NEVER modified.
  2. All generated output goes to latex/output/resume.tex.
  3. Placeholders use {{DOUBLE_BRACES}} — replaced with str.replace(), NOT str.format().
  4. LaTeX special characters in user data are escaped before insertion.
  5. URLs are handled separately and inserted into \\href{URL}{...} without escaping.

Placeholder → generator function mapping:
  {{NAME}}              → profile["name"]
  {{DEGREE_TITLE}}      → profile["degree_title"]
  {{PHONE}}             → profile["phone"]
  {{EMAIL}}             → profile["email"]
  {{LINKEDIN_USERNAME}} → extracted from profile["linkedin"]
  {{GITHUB_USERNAME}}   → extracted from profile["github"]
  {{LOCATION}}          → profile["location"]
  {{SUMMARY}}           → profile["summary"]
  {{EDUCATION}}         → render_education(records)
  {{SKILLS}}            → render_skills(grouped)
  {{PROJECTS}}          → render_projects(records)
  {{CERTIFICATIONS}}    → render_certifications(records)
  {{LANGUAGES}}         → render_languages(records)
  {{INTERESTS}}         → render_interests(records)
"""

from pathlib import Path

from resume_engine.config import config
from resume_engine.validators import (
    latex_escape,
    latex_escape_url,
    extract_username_from_url,
    coerce_list,
)


# ────────────────────────────────────────────────────────────────────
# Deterministic skill category order (matches original resume)
# ────────────────────────────────────────────────────────────────────

_SKILL_CATEGORY_ORDER = [
    "Web Development",
    "Programming Languages",
    "Databases",
    "AI/ML",
    "Other",
]


# ────────────────────────────────────────────────────────────────────
# Section renderers
# ────────────────────────────────────────────────────────────────────

def render_education(records: list[dict]) -> str:
    """
    Generate the LaTeX block for the Education section.

    Matches original resume format exactly:

        \\textbf{Sanjivani College of Engineering, Kopargaon}\\\\
        B.Tech -- Information Technology (CGPA: 8.4) \\hfill 2023 -- Present\\\\
        Higher Secondary Certificate (HSC) \\hfill 65\\%  2023\\\\
        Secondary School Certificate (SSC) \\hfill 88\\%  2021

    The institution+location appears FIRST (bold, line 1).
    The degree + CGPA + date range is on line 2.
    HSC line with score + year is on line 3.
    SSC line with score + year is on line 4.
    """
    if not records:
        return "\\textit{No education records found.}"

    blocks = []
    for rec in records:
        degree      = latex_escape(rec.get("degree", ""))
        field       = latex_escape(rec.get("field", ""))
        institution = latex_escape(rec.get("institution", ""))
        location    = latex_escape(rec.get("location", ""))
        start       = str(rec.get("start_year", "") or "")
        grad_raw    = rec.get("graduation_year")
        cgpa        = latex_escape(str(rec.get("cgpa", "") or ""))
        hsc_score   = latex_escape(str(rec.get("hsc_score", "") or ""))
        hsc_year    = str(rec.get("hsc_year", "") or "")
        ssc_score   = latex_escape(str(rec.get("ssc_score", "") or ""))
        ssc_year    = str(rec.get("ssc_year", "") or "")

        # Institution + Location (line 1, bold)
        inst_loc = ", ".join(p for p in [institution, location] if p)

        # Degree line
        degree_str = " -- ".join(p for p in [degree, field] if p)

        # CGPA inline in degree line if available
        if cgpa:
            degree_str += f" (CGPA: {cgpa})"

        # Date range
        if start and grad_raw:
            date_range = f"{start} -- {latex_escape(str(grad_raw))}"
        elif start:
            date_range = f"{start} -- Present"
        elif grad_raw:
            date_range = str(grad_raw)
        else:
            date_range = ""

        lines = []

        # Line 1: institution (bold)
        if inst_loc:
            lines.append(f"\\textbf{{{inst_loc}}}\\\\")

        # Line 2: degree (CGPA: x) \hfill date
        if degree_str and date_range:
            lines.append(f"{degree_str} \\hfill {date_range}\\\\")
        elif degree_str:
            lines.append(f"{degree_str}\\\\")

        # Line 3: HSC  — double \hfill puts score in centre, year at far right
        if hsc_score or hsc_year:
            parts = []
            if hsc_score:
                parts.append(f"\\hfill {hsc_score}")
            if hsc_year:
                parts.append(f"\\hfill {hsc_year}")
            lines.append(
                f"Higher Secondary Certificate (HSC)" + "".join(parts) + "\\\\"
            )

        # Line 4: SSC  — double \hfill puts score in centre, year at far right
        if ssc_score or ssc_year:
            parts = []
            if ssc_score:
                parts.append(f"\\hfill {ssc_score}")
            if ssc_year:
                parts.append(f"\\hfill {ssc_year}")
            lines.append(
                f"Secondary School Certificate (SSC)" + "".join(parts)
            )

        # Fallback: if no structured HSC/SSC data, render plain details
        if not (hsc_score or hsc_year or ssc_score or ssc_year):
            details = coerce_list(rec.get("details", []))
            if details:
                for detail in details:
                    lines.append(latex_escape(str(detail)) + "\\\\")
                # strip trailing \\ from last
                if lines[-1].endswith("\\\\"):
                    lines[-1] = lines[-1][:-2]

        blocks.append("\n".join(lines))

    return "\n\n\\vspace{4pt}\n".join(blocks)


def render_skills(grouped: dict[str, list[str]]) -> str:
    """
    Generate the LaTeX block for the Skills section.

    Each category becomes one line:
        \\textbf{Category:} Skill1, Skill2, Skill3

    Categories are rendered in the FIXED ORDER defined by _SKILL_CATEGORY_ORDER
    (matching the original resume). Any categories not in that list are appended
    at the end in alphabetical order.
    """
    if not grouped:
        return "\\textit{No skills found.}"

    # Build ordered key list
    ordered_keys = [k for k in _SKILL_CATEGORY_ORDER if k in grouped]
    remaining    = sorted(k for k in grouped if k not in _SKILL_CATEGORY_ORDER)
    all_keys     = ordered_keys + remaining

    lines = []
    for category in all_keys:
        skills = grouped.get(category, [])
        if not skills:
            continue
        cat_escaped    = latex_escape(category)
        skills_escaped = ", ".join(latex_escape(s) for s in skills)
        lines.append(f"\\textbf{{{cat_escaped}:}} {skills_escaped}")

    return "\\\\\n".join(lines)


def render_projects(records: list[dict]) -> str:
    """
    Generate the LaTeX block for the Projects section.

    Matches original resume format:

        \\textbf{Project Name} \\hfill Year \\\\
        Python, Flask, Scikit-learn, XGBoost, Pandas
        \\begin{itemize}[itemsep=0pt, parsep=0pt]
          \\item Bullet description.
        \\end{itemize}

    Notes:
    - Technologies are on their own line WITHOUT a label (no "Technologies:" prefix).
    - Itemize uses [itemsep=0pt, parsep=0pt] for compact spacing.
    - Projects are separated by \\vspace{2pt}.
    """
    if not records:
        return "\\textit{No projects found.}"

    blocks = []
    for proj in records:
        name    = latex_escape(proj.get("name", "Untitled Project"))
        year    = latex_escape(str(proj.get("year", "") or ""))
        techs   = coerce_list(proj.get("technologies", []))
        bullets = coerce_list(proj.get("resume_bullets", []))
        desc    = proj.get("description", "")
        github  = proj.get("github_url", "")
        purl    = proj.get("project_url", "")

        lines = []

        # Header: bold name \hfill year — \\[-3pt] pulls next line up tight
        header = f"\\textbf{{{name}}}"
        if year:
            header += f" \\hfill {year}"
        lines.append(header + "\\\\[-3pt]")

        # Technologies: plain italic, pulled tight to title and bullet
        if techs:
            tech_str = ", ".join(latex_escape(t) for t in techs)
            lines.append(f"\\textit{{{tech_str}}}\\\\[-2pt]")

        # Optional links line
        link_parts = []
        if github:
            link_parts.append(f"\\href{{{latex_escape_url(github)}}}{{GitHub}}")
        if purl:
            link_parts.append(f"\\href{{{latex_escape_url(purl)}}}{{Project}}")
        if link_parts:
            lines.append(" \\textbar\\ ".join(link_parts) + "\\\\[-2pt]")

        # Bullets — topsep=0pt removes the gap between tech line and bullet
        if bullets:
            item_lines = "\n".join(
                f"  \\item {latex_escape(str(b))}" for b in bullets
            )
            lines.append(
                "\\begin{itemize}[itemsep=0pt, parsep=0pt, topsep=0pt]\n"
                + item_lines
                + "\n\\end{itemize}"
            )
        elif desc:
            lines.append(latex_escape(desc))

        blocks.append("\n".join(lines))

    return "\n\n\\vspace{2pt}\n".join(blocks)


def render_certifications(records: list[dict]) -> str:
    """
    Generate the LaTeX block for the Certifications & Awards section.

    Matches original resume format (bullet list):

        \\begin{itemize}[itemsep=0pt, parsep=0pt]
          \\item Cert Name -- Issuer
          \\item ...
        \\end{itemize}

    If a credential_url exists, the name is hyperlinked.
    """
    if not records:
        return "\\textit{No certifications found.}"

    items = []
    for cert in records:
        name   = latex_escape(cert.get("name", ""))
        issuer = latex_escape(cert.get("issuer", ""))
        date   = latex_escape(str(cert.get("date", "") or ""))
        url    = cert.get("credential_url", "")

        if url:
            name_part = f"\\href{{{latex_escape_url(url)}}}{{{name}}}"
        else:
            name_part = name

        parts = [name_part]
        if issuer:
            parts.append(issuer)

        line = " -- ".join(parts)
        if date:
            line += f" \\hfill {date}"

        items.append(f"  \\item {line}")

    item_block = "\n".join(items)
    return (
        "\\begin{itemize}[itemsep=0pt, parsep=0pt]\n"
        + item_block
        + "\n\\end{itemize}"
    )


def render_languages(records: list[dict]) -> str:
    """
    Generate the LaTeX block for the Languages section.

    Matches original resume format (one per line):
        English -- Professional working fluency\\\\
        Hindi -- Full professional fluency\\\\
        Marathi -- Native speaker
    """
    if not records:
        return "\\textit{No languages found.}"

    lines = []
    for lang in records:
        name        = latex_escape(lang.get("name", ""))
        proficiency = latex_escape(lang.get("proficiency", ""))
        if name and proficiency:
            lines.append(f"{name} -- {proficiency}")
        elif name:
            lines.append(name)

    return "\\\\\n".join(lines)


def render_interests(records: list[dict]) -> str:
    """
    Generate the LaTeX block for the Interests section.

    Matches original resume format (one per line):
        Reading Books\\\\
        Exploring Places and New Things
    """
    if not records:
        return "\\textit{No interests found.}"

    names = [latex_escape(i.get("name", "")) for i in records if i.get("name")]
    return "\\\\\n".join(names)


# ────────────────────────────────────────────────────────────────────
# Main renderer
# ────────────────────────────────────────────────────────────────────

def render_resume(resume_data: dict) -> str:
    """
    Take structured resume data and produce a complete LaTeX document string.

    Args:
        resume_data: Dict with keys matching the resume sections.

    Returns:
        The complete filled LaTeX document as a string.

    Raises:
        FileNotFoundError: if the master template is not found.
    """
    template_path = config.LATEX_TEMPLATE_PATH
    if not template_path.exists():
        raise FileNotFoundError(
            f"Master LaTeX template not found: {template_path}\n"
            f"Expected: {template_path}"
        )

    with open(template_path, "r", encoding="utf-8") as f:
        tex = f.read()

    profile        = resume_data.get("profile", {})
    projects       = resume_data.get("projects", [])
    skills         = resume_data.get("skills", {})
    education      = resume_data.get("education", [])
    certifications = resume_data.get("certifications", [])
    languages      = resume_data.get("languages", [])
    interests      = resume_data.get("interests", [])

    # ── Header / contact fields ──────────────────────────────────────
    linkedin_url = profile.get("linkedin", "")
    github_url   = profile.get("github", "")

    replacements = {
        "{{NAME}}":              latex_escape(profile.get("name", "")),
        "{{DEGREE_TITLE}}":      latex_escape(profile.get("degree_title", "")),
        "{{PHONE}}":             latex_escape(profile.get("phone", "")),
        "{{EMAIL}}":             profile.get("email", ""),        # used raw in \href
        "{{LINKEDIN_USERNAME}}": extract_username_from_url(linkedin_url, "linkedin"),
        "{{GITHUB_USERNAME}}":   extract_username_from_url(github_url, "github"),
        "{{LOCATION}}":          latex_escape(profile.get("location", "")),
        "{{SUMMARY}}":           latex_escape(profile.get("summary", "")),
        "{{EDUCATION}}":         render_education(education),
        "{{SKILLS}}":            render_skills(skills),
        "{{PROJECTS}}":          render_projects(projects),
        "{{CERTIFICATIONS}}":    render_certifications(certifications),
        "{{LANGUAGES}}":         render_languages(languages),
        "{{INTERESTS}}":         render_interests(interests),
    }

    for placeholder, value in replacements.items():
        tex = tex.replace(placeholder, value)

    # Sanity check: warn about any remaining unfilled placeholders
    import re
    remaining = re.findall(r"\{\{[A-Z_]+\}\}", tex)
    if remaining:
        print(f"  Warning: Unfilled placeholders remaining in template: {set(remaining)}")

    return tex


def write_tex(tex_content: str) -> Path:
    """
    Write the generated LaTeX content to the output directory.

    The master template is NEVER touched. Only latex/output/resume.tex is written.

    Returns:
        Path to the written .tex file.
    """
    output_dir = config.LATEX_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = config.LATEX_OUTPUT_TEX
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(tex_content)

    return output_path
