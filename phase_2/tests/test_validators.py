"""
test_validators.py — Unit tests for input validation and normalization.

No Gemini. No Firestore. Pure Python.
"""

import pytest
from phase_2.jd_analyzer.validators import (
    validate_jd_input,
    normalize_analysis,
    JDValidationError,
)
from phase_2.jd_analyzer.schemas import JDAnalysis


class TestValidateJDInput:

    def test_valid_jd_returns_stripped(self):
        text = "  We are looking for a Python developer.  "
        result = validate_jd_input(text)
        assert result == "We are looking for a Python developer."

    def test_empty_string_raises(self):
        with pytest.raises(JDValidationError, match="cannot be empty"):
            validate_jd_input("")

    def test_whitespace_only_raises(self):
        with pytest.raises(JDValidationError, match="cannot be empty"):
            validate_jd_input("   \n\t  ")

    def test_non_string_raises(self):
        with pytest.raises(JDValidationError):
            validate_jd_input(None)

    def test_too_short_raises(self):
        with pytest.raises(JDValidationError, match="too short"):
            validate_jd_input("Hi")

    def test_too_long_raises(self):
        with pytest.raises(JDValidationError, match="too long"):
            validate_jd_input("x" * 31_000)

    def test_minimum_length_accepted(self):
        text = "a" * 20
        result = validate_jd_input(text)
        assert result == text

    def test_gemini_not_called_on_empty(self, mocker):
        """Gemini must never be called when validation fails."""
        mock_gemini = mocker.patch("phase_2.jd_analyzer.gemini_client.GeminiClient.analyze_job_description")
        with pytest.raises(JDValidationError):
            validate_jd_input("")
        mock_gemini.assert_not_called()


class TestNormalizeAnalysis:

    def test_dedup_required_skills(self):
        a = JDAnalysis(required_skills=["Python", "python", "PYTHON"])
        result = normalize_analysis(a)
        assert result.required_skills == ["Python"]

    def test_dedup_technologies(self):
        a = JDAnalysis(technologies=["AWS", "aws", "AWS"])
        result = normalize_analysis(a)
        assert result.technologies == ["AWS"]

    def test_react_alias_normalization(self):
        a = JDAnalysis(technologies=["React.js", "React JS"])
        result = normalize_analysis(a)
        assert result.technologies == ["React"]

    def test_restful_alias_normalization(self):
        a = JDAnalysis(required_skills=["RESTful APIs"])
        result = normalize_analysis(a)
        assert result.required_skills == ["REST APIs"]

    def test_nodejs_alias_normalization(self):
        a = JDAnalysis(technologies=["nodejs", "node.js"])
        result = normalize_analysis(a)
        assert result.technologies == ["Node.js"]

    def test_keywords_lowercased(self):
        a = JDAnalysis(keywords=["Python", "Backend", "PYTHON"])
        result = normalize_analysis(a)
        assert result.keywords == ["python", "backend"]

    def test_empty_lists_preserved(self):
        a = JDAnalysis()
        result = normalize_analysis(a)
        assert result.required_skills == []
        assert result.technologies == []

    def test_string_fields_preserved(self):
        a = JDAnalysis(job_title="ML Engineer", company="OpenAI")
        result = normalize_analysis(a)
        assert result.job_title == "ML Engineer"
        assert result.company == "OpenAI"

    def test_no_hallucination_check(self):
        """Normalization must not add items not in the original lists."""
        a = JDAnalysis(technologies=["Python", "Flask"])
        result = normalize_analysis(a)
        assert "Django" not in result.technologies
        assert len(result.technologies) <= 2

    def test_required_vs_preferred_separation(self):
        """Required and preferred lists must remain separate after normalization."""
        a = JDAnalysis(
            required_skills=["Python", "SQL"],
            preferred_skills=["Docker", "Kubernetes"],
        )
        result = normalize_analysis(a)
        assert "Python" in result.required_skills
        assert "SQL" in result.required_skills
        assert "Docker" in result.preferred_skills
        assert "Kubernetes" in result.preferred_skills
        assert "Docker" not in result.required_skills

    def test_missing_info_returns_none_or_empty(self):
        """Fields not present in JD must remain null/empty after normalization."""
        a = JDAnalysis()
        result = normalize_analysis(a)
        assert result.company is None
        assert result.location is None
        assert result.education_requirements == []
