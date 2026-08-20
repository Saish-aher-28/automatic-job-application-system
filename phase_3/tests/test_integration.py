"""
test_integration.py — E2E integration test for Phase 3 matching engine.

Only runs when GEMINI_API_KEY is configured in the environment.
"""

import os
import pytest
from phase_3.matcher.config import config
from phase_3.matcher.firestore_service import (
    _get_firestore_client,
    get_jd_analysis,
    get_user_profile,
    get_user_skills,
    get_user_projects,
    save_match_result,
    get_match_result,
)
from phase_3.matcher.matcher import JDProfileMatcher
from phase_3.matcher.schemas import JobMatchResult

pytestmark = pytest.mark.integration

API_KEY_PRESENT = bool(os.environ.get("GEMINI_API_KEY", "").strip())
REASON = "GEMINI_API_KEY environment variable is not configured."


@pytest.mark.skipif(not API_KEY_PRESENT, reason=REASON)
class TestPhase3Integration:

    def test_e2e_job_matching_pipeline(self):
        # 1. Fetch or create a test JD in Firestore
        db = _get_firestore_client()
        jd_collection = db.collection(config.FIRESTORE_JD_COLLECTION)
        docs = list(jd_collection.limit(1).get())

        if not docs:
            # Seed a minimal JD if none exists in Firestore
            jd_data = {
                "raw_text": "Required: Python, Flask. Preferred: Docker.",
                "analysis": {
                    "job_title": "Backend Engineer",
                    "role_category": "Backend",
                    "required_skills": ["Python", "Flask"],
                    "preferred_skills": ["Docker"],
                    "technologies": ["Python", "Flask", "Docker"],
                    "keywords": ["backend"],
                },
                "model": "gemini-3.1-flash-lite",
                "analysis_version": "1.0",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
            _, doc_ref = jd_collection.add(jd_data)
            jd_doc_id = doc_ref.id
            jd_doc_data = jd_data
        else:
            jd_doc_id = docs[0].id
            jd_doc_data = docs[0].to_dict()

        # 2. Fetch user profile data
        profile_data = get_user_profile()
        skills = get_user_skills()
        projects = get_user_projects()

        # Ensure we have mock skills if Firestore is empty
        if not skills:
            skills = ["Python", "Flask", "PostgreSQL"]

        # Ensure we have mock projects if Firestore is empty
        if not projects:
            projects = [
                {
                    "_id": "integration-proj-1",
                    "name": "Integration Project A",
                    "technologies": ["Python", "Flask"],
                    "description": "Integration test project using Python and Flask.",
                    "resume_bullets": ["Created REST APIs."],
                    "enabled": True,
                }
            ]

        # 3. Match
        matcher = JDProfileMatcher()
        result = matcher.match(
            jd_document_id=jd_doc_id,
            jd_data=jd_doc_data,
            profile_data=profile_data,
            skills=skills,
            projects=projects,
        )

        assert isinstance(result, JobMatchResult)
        assert result.jd_document_id == jd_doc_id
        assert result.overall_match_score >= 0.0
        assert result.overall_match_score <= 100.0
        assert len(result.ranked_projects) == len(projects)

        # 4. Save result
        match_id = save_match_result(result)
        assert match_id is not None

        # 5. Retrieve back and verify
        saved_dict = get_match_result(match_id)
        assert saved_dict["jd_document_id"] == jd_doc_id
        assert saved_dict["scores"]["overall"] == result.overall_match_score
