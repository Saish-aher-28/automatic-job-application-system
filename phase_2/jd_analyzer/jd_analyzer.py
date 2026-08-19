"""
jd_analyzer.py — Orchestrator for the JD analysis pipeline.

Pipeline:
  raw JD text
    → validate_jd_input()
    → GeminiClient.analyze_job_description()
    → normalize_analysis()
    → JDAnalysis
"""

from __future__ import annotations

import logging
from typing import Optional

from phase_2.jd_analyzer.schemas import JDAnalysis
from phase_2.jd_analyzer.validators import validate_jd_input, normalize_analysis
from phase_2.jd_analyzer.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class JDAnalyzer:
    """
    Orchestrates the full JD analysis pipeline.

    Does NOT know about:
      - resume generation
      - project selection
      - Firestore (caller handles persistence)
    """

    def __init__(self, gemini_client: Optional[GeminiClient] = None) -> None:
        self._client = gemini_client or GeminiClient()

    @property
    def model_name(self) -> str:
        return self._client.model_name

    def analyze(self, jd_text: str) -> JDAnalysis:
        """
        Full pipeline: validate → Gemini → normalize → return.

        Args:
            jd_text: Raw job description text.

        Returns:
            Validated and normalized JDAnalysis object.

        Raises:
            JDValidationError: if the input is invalid.
            GeminiAPIError:    if the Gemini call fails.
        """
        logger.info("Validating JD input…")
        cleaned_text = validate_jd_input(jd_text)

        logger.info("Sending JD to Gemini (%s)…", self._client.model_name)
        raw_analysis = self._client.analyze_job_description(cleaned_text)

        logger.info("Normalizing analysis…")
        normalized = normalize_analysis(raw_analysis)

        logger.info("JD analysis complete.")
        return normalized
