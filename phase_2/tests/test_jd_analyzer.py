"""
test_jd_analyzer.py — Tests for the JDAnalyzer orchestrator.

All Gemini calls are mocked. No real API calls.
"""

import pytest
from unittest.mock import MagicMock, patch
from phase_2.jd_analyzer.schemas import JDAnalysis
from phase_2.jd_analyzer.jd_analyzer import JDAnalyzer
from phase_2.jd_analyzer.validators import JDValidationError


VALID_JD = """
We are looking for a Backend Developer with strong Python and Flask skills.
AWS experience is required. Docker is preferred.
2+ years of experience in backend development.
B.Tech in Computer Science preferred.
"""

MINIMAL_ANALYSIS = JDAnalysis(
    job_title="Backend Developer",
    role_category="Backend",
    required_skills=["Python", "Flask", "AWS"],
    preferred_skills=["Docker"],
    technologies=["Python", "Flask", "AWS", "Docker"],
)


def _make_mock_client(return_value: JDAnalysis = MINIMAL_ANALYSIS) -> MagicMock:
    mock = MagicMock()
    mock.model_name = "gemini-3.1-flash-lite"
    mock.analyze_job_description.return_value = return_value
    return mock


class TestJDAnalyzerPipeline:

    def test_valid_jd_returns_analysis(self):
        analyzer = JDAnalyzer(gemini_client=_make_mock_client())
        result = analyzer.analyze(VALID_JD)
        assert isinstance(result, JDAnalysis)
        assert result.job_title == "Backend Developer"

    def test_gemini_called_once(self):
        mock_client = _make_mock_client()
        analyzer = JDAnalyzer(gemini_client=mock_client)
        analyzer.analyze(VALID_JD)
        mock_client.analyze_job_description.assert_called_once()

    def test_empty_jd_raises_before_gemini(self):
        mock_client = _make_mock_client()
        analyzer = JDAnalyzer(gemini_client=mock_client)
        with pytest.raises(JDValidationError):
            analyzer.analyze("")
        mock_client.analyze_job_description.assert_not_called()

    def test_whitespace_jd_raises_before_gemini(self):
        mock_client = _make_mock_client()
        analyzer = JDAnalyzer(gemini_client=mock_client)
        with pytest.raises(JDValidationError):
            analyzer.analyze("   \n   ")
        mock_client.analyze_job_description.assert_not_called()

    def test_normalization_applied_after_gemini(self):
        """Deduplication must happen even if Gemini returns duplicates."""
        raw = JDAnalysis(
            job_title="Developer",
            required_skills=["Python", "python", "PYTHON"],
            technologies=["React.js", "React JS"],
        )
        mock_client = _make_mock_client(return_value=raw)
        analyzer = JDAnalyzer(gemini_client=mock_client)
        result = analyzer.analyze(VALID_JD)
        assert result.required_skills == ["Python"]
        assert result.technologies == ["React"]

    def test_model_name_exposed(self):
        analyzer = JDAnalyzer(gemini_client=_make_mock_client())
        assert analyzer.model_name == "gemini-3.1-flash-lite"

    def test_required_preferred_separated(self):
        analysis = JDAnalysis(
            required_skills=["Python", "SQL"],
            preferred_skills=["Docker", "Kubernetes"],
            technologies=["Python", "SQL", "Docker", "Kubernetes"],
        )
        mock_client = _make_mock_client(return_value=analysis)
        analyzer = JDAnalyzer(gemini_client=mock_client)
        result = analyzer.analyze(VALID_JD)
        assert "Docker" not in result.required_skills
        assert "Docker" in result.preferred_skills

    def test_missing_info_null_and_empty(self):
        analysis = JDAnalysis(
            job_title="Developer",
            # company, location, education intentionally absent
        )
        mock_client = _make_mock_client(return_value=analysis)
        analyzer = JDAnalyzer(gemini_client=mock_client)
        result = analyzer.analyze(VALID_JD)
        assert result.company is None
        assert result.location is None
        assert result.education_requirements == []

    def test_no_hallucination_django_not_added(self):
        """Technologies not in the JD must not appear in results."""
        analysis = JDAnalysis(technologies=["Python", "Flask"])
        mock_client = _make_mock_client(return_value=analysis)
        analyzer = JDAnalyzer(gemini_client=mock_client)
        result = analyzer.analyze(VALID_JD)
        assert "Django" not in result.technologies


class TestGeminiClientMocked:
    """Tests that simulate Gemini API failure scenarios."""

    def test_gemini_api_error_propagated(self):
        from phase_2.jd_analyzer.gemini_client import GeminiAPIError
        mock_client = MagicMock()
        mock_client.model_name = "gemini-3.1-flash-lite"
        mock_client.analyze_job_description.side_effect = GeminiAPIError("API down")
        analyzer = JDAnalyzer(gemini_client=mock_client)
        with pytest.raises(GeminiAPIError, match="API down"):
            analyzer.analyze(VALID_JD)
