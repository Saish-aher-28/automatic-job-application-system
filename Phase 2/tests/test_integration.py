"""
test_integration.py — Integration tests with real Gemini API and Firestore.

Only runs when GEMINI_API_KEY is configured in the environment.
"""

import os
import pytest
from phase_2.jd_analyzer.config import config
from phase_2.jd_analyzer.gemini_client import GeminiClient
from phase_2.jd_analyzer.jd_analyzer import JDAnalyzer
from phase_2.jd_analyzer.firestore_service import save_jd_analysis, get_jd_analysis, _get_firestore_client
from phase_2.jd_analyzer.schemas import JDAnalysis

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration

# Only run if GEMINI_API_KEY is available and valid
API_KEY_PRESENT = bool(os.environ.get("GEMINI_API_KEY", "").strip())
REASON = "GEMINI_API_KEY environment variable is not set"


@pytest.mark.skipif(not API_KEY_PRESENT, reason=REASON)
class TestRealGeminiAndFirestoreIntegration:

    def test_real_gemini_analysis_and_firestore_store(self):
        # A simple valid JD text
        jd_text = (
            "We are seeking a Software Engineer. "
            "Python and SQL are required. Docker is preferred. "
            "Responsibilities include designing backend systems. "
            "Degree in Computer Science is required."
        )

        analyzer = JDAnalyzer()
        analysis = analyzer.analyze(jd_text)

        # 1. Verify schema structure & values
        assert isinstance(analysis, JDAnalysis)
        assert analysis.job_title is not None
        assert "python" in [s.lower() for s in analysis.required_skills]
        assert "sql" in [s.lower() for s in analysis.required_skills]
        assert "docker" in [s.lower() for s in analysis.preferred_skills]

        # 2. Verify Firestore saving and retrieval
        doc_id = save_jd_analysis(jd_text, analysis, analyzer.model_name)
        assert doc_id is not None
        assert isinstance(doc_id, str)

        retrieved = get_jd_analysis(doc_id)
        assert retrieved["raw_text"] == jd_text
        assert retrieved["model"] == analyzer.model_name
        assert retrieved["analysis"]["job_title"] == analysis.job_title

    def test_five_different_jd_types(self):
        """
        STEP 16: Test five different JD types.
        1. Backend Developer
        2. Frontend Developer
        3. Machine Learning Engineer
        4. DevOps Engineer
        5. Data Analyst
        """
        jds = {
            "backend": (
                "Backend Developer position. Required: Python, Django, PostgreSQL. "
                "Preferred: AWS, Docker. Responsibility: Design APIs."
            ),
            "frontend": (
                "Frontend Developer. Required: React, TypeScript, CSS. "
                "Preferred: Next.js, Tailwind. Experience: 2+ years frontend development."
            ),
            "ml": (
                "Machine Learning Engineer. Required: Python, PyTorch, Scikit-learn. "
                "Preferred: AWS SageMaker, Docker. Education: Master's in CS or equivalent."
            ),
            "devops": (
                "DevOps Engineer. Required: Linux, Docker, Terraform, CI/CD. "
                "Preferred: Kubernetes, AWS. Location: Remote."
            ),
            "data_analyst": (
                "Data Analyst. Required: SQL, Excel, Tableau. "
                "Preferred: Python, PowerBI. Responsibilities: Create dashboards."
            ),
        }

        analyzer = JDAnalyzer()
        doc_ids = []

        for role, text in jds.items():
            analysis = analyzer.analyze(text)
            assert isinstance(analysis, JDAnalysis)
            assert analysis.job_title is not None

            # Save to Firestore
            doc_id = save_jd_analysis(text, analysis, analyzer.model_name)
            assert doc_id is not None
            doc_ids.append(doc_id)

        # Verify we got 5 distinct document IDs
        assert len(doc_ids) == 5
        assert len(set(doc_ids)) == 5
