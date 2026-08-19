"""
test_gemini_client.py — Tests for GeminiClient retry and error handling.

All tests mock the Gemini SDK — no real API calls.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from phase_2.jd_analyzer.gemini_client import GeminiClient, GeminiAPIError, GeminiConfigError
from phase_2.jd_analyzer.schemas import JDAnalysis


SAMPLE_ANALYSIS = JDAnalysis(
    job_title="Backend Developer",
    required_skills=["Python", "Flask"],
    technologies=["Python", "Flask"],
)


def _make_client_with_mock_sdk(mock_response=None, side_effect=None):
    """Create a GeminiClient with the internal SDK call mocked."""
    client = GeminiClient.__new__(GeminiClient)
    client._api_key     = "test-key"
    client._model       = "gemini-3.1-flash-lite"
    client._max_retries = 3

    inner_mock = MagicMock()
    if side_effect:
        inner_mock.side_effect = side_effect
    else:
        resp = MagicMock()
        resp.parsed = mock_response or SAMPLE_ANALYSIS
        inner_mock.return_value = resp

    client._client = MagicMock()
    client._client.models.generate_content = inner_mock
    client._types  = MagicMock()
    client._types.GenerateContentConfig = MagicMock()
    return client, inner_mock


class TestGeminiClientRetry:

    def test_success_on_first_attempt(self):
        client, inner = _make_client_with_mock_sdk()
        result = client.analyze_job_description("We need a Python developer with 2 years experience.")
        assert isinstance(result, JDAnalysis)
        inner.assert_called_once()

    def test_retries_on_transient_error(self):
        """Client should retry up to MAX_RETRIES on transient failures."""
        responses = [
            Exception("connection reset"),
            Exception("timeout"),
            MagicMock(parsed=SAMPLE_ANALYSIS),
        ]

        client = GeminiClient.__new__(GeminiClient)
        client._api_key = "test-key"
        client._model = "gemini-3.1-flash-lite"
        client._max_retries = 3
        client._types = MagicMock()
        client._types.GenerateContentConfig = MagicMock()

        call_count = [0]

        def fake_call(*args, **kwargs):
            i = call_count[0]
            call_count[0] += 1
            r = responses[i]
            if isinstance(r, Exception):
                raise r
            return r

        client._client = MagicMock()
        client._client.models.generate_content.side_effect = fake_call

        # Patch sleep to avoid waiting in tests
        with patch("phase_2.jd_analyzer.gemini_client.time.sleep"):
            result = client.analyze_job_description("Valid JD with enough text to pass validation.")

        assert isinstance(result, JDAnalysis)
        assert call_count[0] == 3

    def test_raises_after_max_retries(self):
        client = GeminiClient.__new__(GeminiClient)
        client._api_key = "test-key"
        client._model = "gemini-3.1-flash-lite"
        client._max_retries = 3
        client._types = MagicMock()
        client._types.GenerateContentConfig = MagicMock()
        client._client = MagicMock()
        client._client.models.generate_content.side_effect = Exception("persistent error")

        with patch("phase_2.jd_analyzer.gemini_client.time.sleep"):
            with pytest.raises(GeminiAPIError, match="persistent error"):
                client.analyze_job_description("Some valid JD text that is long enough.")

    def test_permanent_gemini_api_error_not_retried(self):
        """GeminiAPIError itself should not trigger a retry."""
        client = GeminiClient.__new__(GeminiClient)
        client._api_key = "test-key"
        client._model = "gemini-3.1-flash-lite"
        client._max_retries = 3
        client._types = MagicMock()
        client._types.GenerateContentConfig = MagicMock()
        client._client = MagicMock()
        client._client.models.generate_content.side_effect = GeminiAPIError("empty response")

        with pytest.raises(GeminiAPIError):
            client.analyze_job_description("Some valid JD text long enough to test.")

        # Should have been called only once
        assert client._client.models.generate_content.call_count == 1


class TestGeminiConfigError:

    def test_missing_api_key_raises(self):
        with patch("phase_2.jd_analyzer.gemini_client.config") as mock_cfg:
            mock_cfg.GEMINI_API_KEY = ""
            mock_cfg.GEMINI_MODEL   = "gemini-3.1-flash-lite"
            mock_cfg.MAX_RETRIES    = 3
            with pytest.raises(GeminiConfigError, match="GEMINI_API_KEY"):
                GeminiClient(api_key="")
