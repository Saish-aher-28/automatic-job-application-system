"""
test_semantic_matcher.py — Tests for SemanticMatcher retry and schema validation.

All tests mock the Gemini SDK — no real API calls.
"""

import pytest
from unittest.mock import MagicMock, patch
from phase_3.matcher.semantic_matcher import SemanticMatcher
from phase_3.matcher.schemas import ProjectSemanticMatch


SAMPLE_SEMANTIC_RESPONSE = ProjectSemanticMatch(
    relevance_score=85.0,
    matched_requirements=["Python", "AWS"],
    supporting_evidence=["Project uses Python Flask.", "Deployed on AWS S3."],
    missing_requirements=["Docker"],
    reason="Strong backend alignment.",
)

SAMPLE_JD = {
    "job_title": "Backend Developer",
    "required_skills": ["Python", "AWS"],
    "preferred_skills": ["Docker"],
    "technologies": ["Python", "AWS", "Docker"],
}

SAMPLE_PROJECT = {
    "name": "CloudReport",
    "technologies": ["Python", "AWS"],
    "description": "AWS reporting tool using Python.",
}


class TestSemanticMatcherMocked:

    def test_relevance_score_validation(self):
        # relevance_score must be between 0 and 100
        with pytest.raises(ValueError):
            ProjectSemanticMatch(
                relevance_score=150.0,  # invalid
                matched_requirements=[],
                supporting_evidence=[],
                missing_requirements=[],
                reason="Invalid",
            )

    @patch("phase_3.matcher.semantic_matcher.config")
    def test_semantic_matcher_success_first_attempt(self, mock_config):
        mock_config.GEMINI_API_KEY = "test-key"
        mock_config.GEMINI_MODEL   = "gemini-3.1-flash-lite"
        mock_config.MAX_RETRIES    = 3

        matcher = SemanticMatcher.__new__(SemanticMatcher)
        matcher._api_key = "test-key"
        matcher._model = "gemini-3.1-flash-lite"
        matcher._types = MagicMock()
        matcher._types.GenerateContentConfig = MagicMock()

        # Mock the client's generate_content call
        mock_resp = MagicMock()
        mock_resp.parsed = SAMPLE_SEMANTIC_RESPONSE
        matcher._client = MagicMock()
        matcher._client.models.generate_content.return_value = mock_resp

        result = matcher.evaluate_project_relevance(SAMPLE_JD, SAMPLE_PROJECT)
        assert isinstance(result, ProjectSemanticMatch)
        assert result.relevance_score == 85.0
        matcher._client.models.generate_content.assert_called_once()

    @patch("phase_3.matcher.semantic_matcher.config")
    def test_semantic_matcher_retries_and_succeeds(self, mock_config):
        mock_config.GEMINI_API_KEY = "test-key"
        mock_config.GEMINI_MODEL   = "gemini-3.1-flash-lite"
        mock_config.MAX_RETRIES    = 3

        matcher = SemanticMatcher.__new__(SemanticMatcher)
        matcher._api_key = "test-key"
        matcher._model = "gemini-3.1-flash-lite"
        matcher._types = MagicMock()
        matcher._types.GenerateContentConfig = MagicMock()

        # Fail twice, succeed third
        responses = [
            Exception("Connection reset"),
            Exception("Timeout"),
            MagicMock(parsed=SAMPLE_SEMANTIC_RESPONSE)
        ]
        call_count = [0]

        def fake_call(*args, **kwargs):
            i = call_count[0]
            call_count[0] += 1
            r = responses[i]
            if isinstance(r, Exception):
                raise r
            return r

        matcher._client = MagicMock()
        matcher._client.models.generate_content.side_effect = fake_call

        with patch("phase_3.matcher.semantic_matcher.time.sleep"):
            result = matcher.evaluate_project_relevance(SAMPLE_JD, SAMPLE_PROJECT)

        assert isinstance(result, ProjectSemanticMatch)
        assert result.relevance_score == 85.0
        assert call_count[0] == 3

    @patch("phase_3.matcher.semantic_matcher.config")
    def test_semantic_matcher_raises_after_max_retries(self, mock_config):
        mock_config.GEMINI_API_KEY = "test-key"
        mock_config.GEMINI_MODEL   = "gemini-3.1-flash-lite"
        mock_config.MAX_RETRIES    = 3

        matcher = SemanticMatcher.__new__(SemanticMatcher)
        matcher._api_key = "test-key"
        matcher._model = "gemini-3.1-flash-lite"
        matcher._types = MagicMock()
        matcher._types.GenerateContentConfig = MagicMock()
        matcher._client = MagicMock()
        matcher._client.models.generate_content.side_effect = Exception("Persistent connection error")

        with patch("phase_3.matcher.semantic_matcher.time.sleep"):
            with pytest.raises(RuntimeError, match="Failed to evaluate project semantic relevance"):
                matcher.evaluate_project_relevance(SAMPLE_JD, SAMPLE_PROJECT)
