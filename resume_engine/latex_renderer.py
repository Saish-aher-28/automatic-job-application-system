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
# Section renderers
# ────────────────────────────────────────────────────────────────────

def render_education(records: list[dict]) -> str:
    """
    Generate the LaTeX block for the Education section.

    Each record produces a block:
        \\textbf{Degree in Field} \\hfill Start – Graduation\\\\
        Institution, Location\\\\
        Detail 1 | Detail 2 | ...

    Multiple records are separated by \\vspace{4pt}.
    """
    if not records:
        return "\\textit{No education records found.}"

    blocks = []
    for rec in records:
        degree     = latex_escape(rec.get("degree", ""))
        field      = latex_escape(rec.get("field", ""))
        spec       = latex_escape(rec.get("specialization", ""))
        institution= latex_escape(rec.get("institution", ""))
        location   = latex_escape(rec.get("location", ""))
        start      = str(rec.get("start_year", "") or "")
        grad       = str(rec.get("graduation_year", "") or "")
        details    = coerce_list(rec.get("details", []))

        # Build degree line
        degree_parts = [p for p in [degree, field] if p]
        degree_line  = " in ".join(degree_parts) if degree_parts else ""
        if spec:
            degree_line += f", {spec}"

        # Date range
        if start and grad:
            date_range = f"{start} -- {grad}"
        elif grad:
            date_range = str(grad)
        elif start:
            date_range = str(start)
        else:
            date_range = ""

        lines = []
        if degree_line or date_range:
            lines.append(
                f"\\textbf{{{degree_line}}} \\hfill {date_range}\\\\"
            )
        if institution or location:
            inst_loc = ", ".join(p for p in [institution, location] if p)
            lines.append(f"{inst_loc}\\\\")

        if details:
            escaped_details = [latex_escape(str(d)) for d in details]
            lines.append(" \\textbar\\ ".join(escaped_details))

        blocks.append("\n".join(lines))

    return "\n\n\\vspace{4pt}\n".join(blocks)


def render_skills(grouped: dict[str, list[str]]) -> str:
    """
    Generate the LaTeX block for the Skills section.

    Each category becomes one line:
        \\textbf{Category:} Skill1, Skill2, Skill3

    Categories are rendered in their natural order (from Firestore sort).
    """
    if not grouped:
        return "\\textit{No skills found.}"

    lines = []
    for category, skills in grouped.items():
        if not skills:
            continue
        cat_escaped    = latex_escape(category)
        skills_escaped = ", ".join(latex_escape(s) for s in skills)
        lines.append(f"\\textbf{{{cat_escaped}:}} {skills_escaped}")

    return "\\\\\n".join(lines)


def render_projects(records: list[dict]) -> str:
    """
    Generate the LaTeX block for the Projects section.

    Each project block:
        \\textbf{Project Name} \\hfill Year
        Technologies: Tech1, Tech2, ...
        \\begin{itemize}
          \\item Bullet 1
          \\item Bullet 2
        \\end{itemize}

    Projects are separated by \\vspace{2pt}.
    """
    if not records:
        return "\\textit{No projects found.}"

    blocks = []
    for proj in records:
        name   = latex_escape(proj.get("name", "Untitled Project"))
        year   = latex_escape(str(proj.get("year", "") or ""))
        techs  = coerce_list(proj.get("technologies", []))
        bullets = coerce_list(proj.get("resume_bullets", []))
        desc   = proj.get("description", "")
        github = proj.get("github_url", "")
        purl   = proj.get("project_url", "")

        lines = []

        # Header line: name + year
        header = f"\\textbf{{{name}}}"
        if year:
            header += f" \\hfill {year}"
        lines.append(header + "\\\\[-3pt]")

        # Technologies line
        if techs:
            tech_str = ", ".join(latex_escape(t) for t in techs)
            lines.append(f"\\textit{{Technologies:}} {tech_str}\\\\[-3pt]")

        # Links (GitHub / Project URL)
        link_parts = []
        if github:
            link_parts.append(f"\\href{{{latex_escape_url(github)}}}{{GitHub}}")
        if purl:
            link_parts.append(f"\\href{{{latex_escape_url(purl)}}}{{Project}}")
        if link_parts:
            lines.append(" \\textbar\\ ".join(link_parts) + "\\\\[-3pt]")

        # Bullets (preferred) or fallback to description
        if bullets:
            item_lines = "\n".join(
                f"  \\item {latex_escape(str(b))}" for b in bullets
            )
            lines.append(
                "\\begin{itemize}\n" + item_lines + "\n\\end{itemize}"
            )
        elif desc:
            lines.append(latex_escape(desc))

        blocks.append("\n".join(lines))

    return "\n\n\\vspace{2pt}\n".join(blocks)


def render_certifications(records: list[dict]) -> str:
    """
    Generate the LaTeX block for the Certifications & Awards section.

    Each entry:
        \\textbf{Cert Name} -- Issuer \\hfill Date

    or, if a credential_url exists:
        \\href{url}{\\textbf{Cert Name}} -- Issuer \\hfill Date
    """
    if not records:
        return "\\textit{No certifications found.}"

    lines = []
    for cert in records:
        name   = latex_escape(cert.get("name", ""))
        issuer = latex_escape(cert.get("issuer", ""))
        date   = latex_escape(str(cert.get("date", "") or ""))
        url    = cert.get("credential_url", "")

        if url:
            name_part = f"\\href{{{latex_escape_url(url)}}}{{\\textbf{{{name}}}}}"
        else:
            name_part = f"\\textbf{{{name}}}"

        parts = [name_part]
        if issuer:
            parts.append(issuer)

        line = " -- ".join(parts)
        if date:
            line += f" \\hfill {date}"

        lines.append(line)

    return "\\\\\n".join(lines)


def render_languages(records: list[dict]) -> str:
    """
    Generate the LaTeX block for the Languages section.

    Format:
        English -- Professional working fluency \\quad Hindi -- Full professional fluency

    All on one line separated by \\quad for compact spacing,
    or line-break separated if preferred.
    """
    if not records:
        return "\\textit{No languages found.}"

    parts = []
    for lang in records:
        name        = latex_escape(lang.get("name", ""))
        proficiency = latex_escape(lang.get("proficiency", ""))
        if name and proficiency:
            parts.append(f"{name} -- {proficiency}")
        elif name:
            parts.append(name)

    return " \\quad \\textbar\\ \\quad ".join(parts)


def render_interests(records: list[dict]) -> str:
    """
    Generate the LaTeX block for the Interests section.

    Format: comma-separated on a single line.
    Example: Reading Books, Chess, Open Source Contributions
    """
    if not records:
        return "\\textit{No interests found.}"

    names = [latex_escape(i.get("name", "")) for i in records if i.get("name")]
    return ", ".join(names)


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

    profile      = resume_data.get("profile", {})
    projects     = resume_data.get("projects", [])
    skills       = resume_data.get("skills", {})
    education    = resume_data.get("education", [])
    certifications = resume_data.get("certifications", [])
    languages    = resume_data.get("languages", [])
    interests    = resume_data.get("interests", [])

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
        print(f"  ⚠  Unfilled placeholders remaining in template: {set(remaining)}")

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
