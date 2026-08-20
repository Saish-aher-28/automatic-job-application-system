"""
semantic_matcher.py — Stage 2 semantic relevance evaluation using Gemini.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from phase_3.matcher.config import config
from phase_3.matcher.schemas import ProjectSemanticMatch

logger = logging.getLogger(__name__)


# ── System Instructions ──────────────────────────────────────────────────────
SEMANTIC_SYSTEM_PROMPT = """\
You are a Project Relevance Evaluator.
Your job is to compare a structured Job Description against a user's Project details, and determine the project's semantic relevance to the job.

STRICT RULES:
1. Evaluate ONLY the supplied project details against the supplied Job Description.
2. relevance_score must be a float between 0.0 and 100.0. Assign a high score (85+) only for projects showing deep and direct alignment with key JD technologies and responsibilities. Assign a low score (<40) if the project is unrelated.
3. matched_requirements must be a list of requirements (skills, technologies, categories) from the JD that this project demonstrated.
4. supporting_evidence must list concrete facts (tools, languages, statements) directly present in the project details that prove the match.
5. missing_requirements must list requirements from the JD that are absent in the project details.
6. Do NOT assume, invent, or extrapolate. If a technology or skill is not explicitly mentioned in the project, it is NOT matched. Do NOT assume "the project probably used Docker" if Docker is not listed.
7. Return ONLY the structured JSON output — no explanations, no recommendations, no additional text.
"""


def build_semantic_user_prompt(jd_data: dict, project: dict) -> str:
    """Constructs a clean representation of the JD and project details for the prompt."""
    return f"""\
### JOB DESCRIPTION
Job Title: {jd_data.get('job_title', 'Untitled')}
Role Category: {jd_data.get('role_category', 'Unspecified')}
Required Skills: {', '.join(jd_data.get('required_skills', []))}
Preferred Skills: {', '.join(jd_data.get('preferred_skills', []))}
Technologies: {', '.join(jd_data.get('technologies', []))}

### PROJECT DETAILS
Project Name: {project.get('name', 'Untitled')}
Technologies Used: {', '.join(project.get('technologies', []))}
Keywords/Categories: {', '.join((project.get('keywords', []) or []) + (project.get('categories', []) or []))}
Description: {project.get('description', '')}
Resume Bullets:
{chr(10).join(' - ' + str(b) for b in project.get('resume_bullets', []))}

Evaluate this project's relevance.
"""


class SemanticMatcher:
    """
    Evaluates project candidates semantically using Gemini.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self._api_key = api_key or config.GEMINI_API_KEY
        self._model   = model   or config.GEMINI_MODEL

        if not self._api_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is not configured.\n"
                "Add it to your .env file."
            )

        try:
            from google import genai
            from google.genai import types as genai_types
        except ImportError as exc:
            raise RuntimeError(
                "google-genai package is not installed.\n"
                "Run: pip install google-genai"
            ) from exc

        self._client = genai.Client(api_key=self._api_key)
        self._types  = genai_types

    def evaluate_project_relevance(self, jd_data: dict, project: dict) -> ProjectSemanticMatch:
        """
        Calls Gemini to evaluate a project's relevance against the JD.
        Implements Configurable Retry Logic.
        """
        last_exc: Optional[Exception] = None

        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                logger.info(
                    "Sending project '%s' to Gemini for semantic match (attempt %d/%d)...",
                    project.get("name"), attempt, config.MAX_RETRIES
                )
                result = self._call_gemini(jd_data, project)
                return result
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning("Gemini evaluation attempt %d failed: %s", attempt, exc)
                if attempt < config.MAX_RETRIES:
                    wait = 2 ** (attempt - 1)
                    time.sleep(wait)

        raise RuntimeError(
            f"Failed to evaluate project semantic relevance after {config.MAX_RETRIES} attempts. "
            f"Last error: {last_exc}"
        ) from last_exc

    def _call_gemini(self, jd_data: dict, project: dict) -> ProjectSemanticMatch:
        """Helper to invoke Gemini API with schema validation."""
        response = self._client.models.generate_content(
            model=self._model,
            contents=build_semantic_user_prompt(jd_data, project),
            config=self._types.GenerateContentConfig(
                system_instruction=SEMANTIC_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ProjectSemanticMatch,
                temperature=0.1,  # low temperature for stable evidence parsing
            ),
        )

        if hasattr(response, "parsed") and response.parsed is not None:
            parsed = response.parsed
            if isinstance(parsed, ProjectSemanticMatch):
                return parsed
            return ProjectSemanticMatch.model_validate(parsed)

        # fallback parsing
        import json
        raw_text = response.text
        if not raw_text:
            raise RuntimeError("Gemini returned empty semantic evaluation.")
        data = json.loads(raw_text)
        return ProjectSemanticMatch.model_validate(data)
