"""
test_adversarial_safety.py — Unit tests verifying Gemini hallucination protection.

Ensures that if Gemini claims a match for a technology not explicitly supported
by project details, the validation layer rejects it.
"""

import pytest
from unittest.mock import MagicMock, patch
from phase_3.matcher.semantic_matcher import SemanticMatcher
from phase_3.matcher.schemas import ProjectSemanticMatch


class TestAdversarialHallucinationProtection:

    @pytest.fixture
    def mock_matcher(self):
        """Create a SemanticMatcher with config mocked so it doesn't try to connect to Gemini."""
        with patch("phase_3.matcher.semantic_matcher.config") as mock_cfg:
            mock_cfg.GEMINI_API_KEY = "test-key"
            mock_cfg.GEMINI_MODEL   = "gemini-3.1-flash-lite"
            mock_cfg.MAX_RETRIES    = 3
            
            # Instantiate
            matcher = SemanticMatcher.__new__(SemanticMatcher)
            matcher._api_key = "test-key"
            matcher._model = "gemini-3.1-flash-lite"
            matcher._types = MagicMock()
            matcher._types.GenerateContentConfig = MagicMock()
            return matcher

    def test_adversarial_1_kubernetes_vs_docker_aws(self, mock_matcher):
        """
        Adversarial Test #1 (Req 18):
        JD requires Kubernetes. Project details only mention Docker and AWS.
        Gemini response tries to claim Kubernetes matched.
        Validation layer must reject Kubernetes.
        """
        project = {
            "name": "Cloud Deployment Tool",
            "technologies": ["Docker", "AWS"],
            "description": "Automated cloud deployment using Docker and AWS.",
            "resume_bullets": [
                "Built containerized deployment workflow.",
                "Configured AWS infrastructure."
            ]
        }

        # Mock Gemini returned raw result with hallucination
        raw_result = ProjectSemanticMatch(
            relevance_score=90.0,
            matched_requirements=["Kubernetes", "AWS"],
            supporting_evidence=["Deployment uses containers.", "Deployed to AWS."],
            missing_requirements=[],
            reason="Good cloud fit."
        )

        validated = mock_matcher._validate_and_sanitize(raw_result, project)

        # Kubernetes must be rejected
        assert "Kubernetes" not in validated.matched_requirements
        assert "AWS" in validated.matched_requirements
        assert "Kubernetes" in validated.missing_requirements
        # Score must be reduced proportionally: 90.0 * (1 / 2) = 45.0
        assert validated.relevance_score == 45.0

    def test_adversarial_2_react_vs_react_native(self, mock_matcher):
        """
        Adversarial Test #2 (Req 19):
        JD requires React. Project only contains React Native.
        React and React Native are distinct. React must be rejected.
        """
        project = {
            "name": "Mobile Application",
            "technologies": ["React Native"],
            "description": "Built a mobile app for iOS and Android.",
            "resume_bullets": ["Used React Native components."]
        }

        raw_result = ProjectSemanticMatch(
            relevance_score=80.0,
            matched_requirements=["React"],
            supporting_evidence=["Used React components."],
            missing_requirements=[],
            reason="React mobile framework fit."
        )

        validated = mock_matcher._validate_and_sanitize(raw_result, project)

        assert "React" not in validated.matched_requirements
        assert "React" in validated.missing_requirements
        assert validated.relevance_score == 0.0

    def test_adversarial_3_java_vs_javascript(self, mock_matcher):
        """
        Adversarial Test #3 (Req 20):
        JD requires JavaScript. Project only contains Java.
        They are different. JavaScript must be rejected.
        """
        project = {
            "name": "Enterprise Core System",
            "technologies": ["Java"],
            "description": "Enterprise API service written in Java.",
            "resume_bullets": ["Optimized backend Java threads."]
        }

        raw_result = ProjectSemanticMatch(
            relevance_score=75.0,
            matched_requirements=["JavaScript"],
            supporting_evidence=["Uses Java scripting."],
            missing_requirements=[],
            reason="Enterprise language fit."
        )

        validated = mock_matcher._validate_and_sanitize(raw_result, project)

        assert "JavaScript" not in validated.matched_requirements
        assert "JavaScript" in validated.missing_requirements
        assert validated.relevance_score == 0.0

    def test_adversarial_4_postgresql_vs_mongodb(self, mock_matcher):
        """
        Adversarial Test #4 (Req 21):
        JD requires PostgreSQL. Project contains MongoDB.
        PostgreSQL must be rejected.
        """
        project = {
            "name": "Social Analytics Dashboard",
            "technologies": ["MongoDB"],
            "description": "Dashboard collecting posts in MongoDB document store.",
            "resume_bullets": ["Stored JSON analytics in MongoDB."]
        }

        raw_result = ProjectSemanticMatch(
            relevance_score=60.0,
            matched_requirements=["PostgreSQL"],
            supporting_evidence=["Uses NoSQL database storage."],
            missing_requirements=[],
            reason="Uses modern database."
        )

        validated = mock_matcher._validate_and_sanitize(raw_result, project)

        assert "PostgreSQL" not in validated.matched_requirements
        assert "PostgreSQL" in validated.missing_requirements
        assert validated.relevance_score == 0.0

    def test_adversarial_5_kubernetes_vs_docker(self, mock_matcher):
        """
        Adversarial Test #5 (Req 22):
        JD requires Kubernetes. Project contains Docker.
        Kubernetes must be rejected.
        """
        project = {
            "name": "Local Runner",
            "technologies": ["Docker"],
            "description": "Runs local tests using Docker compose.",
            "resume_bullets": ["Built local Docker test image."]
        }

        raw_result = ProjectSemanticMatch(
            relevance_score=50.0,
            matched_requirements=["Kubernetes"],
            supporting_evidence=["Uses container systems."],
            missing_requirements=[],
            reason="Container fit."
        )

        validated = mock_matcher._validate_and_sanitize(raw_result, project)

        assert "Kubernetes" not in validated.matched_requirements
        assert "Kubernetes" in validated.missing_requirements
        assert validated.relevance_score == 0.0

    def test_weak_project_semantic_score(self, mock_matcher):
        """
        Semantic score safety (Req 26):
        Weak project (Transportation React/Firebase App) vs Machine Learning JD
        must receive extremely low matching score.
        """
        project = {
            "name": "Transportation Shipment App",
            "technologies": ["React", "Firebase"],
            "description": "React-based shipment tracker app using Firebase storage.",
            "resume_bullets": ["Styled frontend layout."]
        }

        raw_result = ProjectSemanticMatch(
            relevance_score=90.0,  # artificially high score returned by a faulty mock/call
            matched_requirements=["Python", "PyTorch", "Machine Learning"],  # completely hallucinated
            supporting_evidence=["Mentions tracker app."],
            missing_requirements=[],
            reason="High alignment."
        )

        validated = mock_matcher._validate_and_sanitize(raw_result, project)

        # All hallucinated requirements must be filtered out
        assert len(validated.matched_requirements) == 0
        assert validated.relevance_score == 0.0
