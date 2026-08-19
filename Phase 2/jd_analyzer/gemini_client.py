"""
gemini_client.py — Gemini API client for JD analysis.

Isolated here so the rest of the system never touches the Gemini SDK directly.
Only this module knows about google-genai.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from phase_2.jd_analyzer.config import config
from phase_2.jd_analyzer.schemas import JDAnalysis
from phase_2.jd_analyzer.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


class GeminiConfigError(RuntimeError):
    """Raised when Gemini API key or model is not configured."""


class GeminiAPIError(RuntimeError):
    """Raised for unrecoverable Gemini API failures."""


class GeminiClient:
    """
    Thin wrapper around google-genai for JD analysis.

    Usage:
        client = GeminiClient()
        analysis = client.analyze_job_description(jd_text)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self._api_key    = api_key    or config.GEMINI_API_KEY
        self._model      = model      or config.GEMINI_MODEL
        self._max_retries = max_retries if max_retries is not None else config.MAX_RETRIES

        if not self._api_key:
            raise GeminiConfigError(
                "GEMINI_API_KEY is not set.\n"
                "Add it to your .env file:\n"
                "  GEMINI_API_KEY=your-key-here\n"
                "Get a key at: https://aistudio.google.com/app/apikey"
            )

        # Lazy import — keeps import errors scoped to this module
        try:
            from google import genai
            from google.genai import types as genai_types
        except ImportError as exc:
            raise GeminiConfigError(
                "google-genai package is not installed.\n"
                "Run: pip install google-genai"
            ) from exc

        self._client = genai.Client(api_key=self._api_key)
        self._types  = genai_types

    @property
    def model_name(self) -> str:
        return self._model

    def analyze_job_description(self, jd_text: str) -> JDAnalysis:
        """
        Send a JD to Gemini and return a validated JDAnalysis object.

        Retries on transient errors up to MAX_RETRIES times.
        Raises GeminiAPIError on permanent failure.
        """
        last_exc: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                logger.info(
                    "Sending JD to Gemini (%s) — attempt %d/%d",
                    self._model, attempt, self._max_retries,
                )
                result = self._call_gemini(jd_text)
                logger.info("Structured response received from Gemini.")
                return result

            except (GeminiAPIError,):
                raise   # permanent — don't retry

            except Exception as exc:  # noqa: BLE001  transient
                last_exc = exc
                logger.warning("Gemini attempt %d failed: %s", attempt, exc)
                if attempt < self._max_retries:
                    wait = 2 ** (attempt - 1)   # 1s, 2s, 4s …
                    logger.info("Retrying in %ds…", wait)
                    time.sleep(wait)

        raise GeminiAPIError(
            f"Gemini API failed after {self._max_retries} attempts. "
            f"Last error: {last_exc}"
        ) from last_exc

    def _call_gemini(self, jd_text: str) -> JDAnalysis:
        """Single Gemini API call with structured output."""
        response = self._client.models.generate_content(
            model=self._model,
            contents=build_user_prompt(jd_text),
            config=self._types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=JDAnalysis,
                temperature=0.1,   # low temperature for deterministic extraction
            ),
        )

        # Prefer the SDK's parsed attribute when available
        if hasattr(response, "parsed") and response.parsed is not None:
            parsed = response.parsed
            if isinstance(parsed, JDAnalysis):
                return parsed
            # Dict returned — coerce through Pydantic
            return JDAnalysis.model_validate(parsed)

        # Fallback: parse text
        import json
        raw_text = response.text
        if not raw_text:
            raise GeminiAPIError("Gemini returned an empty response.")

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise GeminiAPIError(
                f"Gemini returned non-JSON output: {raw_text[:200]}"
            ) from exc

        return JDAnalysis.model_validate(data)
