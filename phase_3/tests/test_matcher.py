"""
test_matcher.py — Unit tests for the full matching orchestrator pipeline (mocked API/DB).
"""

import pytest
from unittest.mock import MagicMock
from phase_3.matcher.matcher import JDProfileMatcher
from phase_3.matcher.schemas import JobMatchResult, ProjectSemanticMatch


# ── Sample Data ──────────────────────────────────────────────────────────────
SAMPLE_JD_DATA = {
    "analysis": {
        "job_title": "Backend Developer",
        "role_category": "Backend",
        "required_skills": ["Python", "Flask", "PostgreSQL"],
        "preferred_skills": ["Docker", "Kubernetes"],
        "technologies": ["Python", "Flask", "PostgreSQL", "Docker", "Kubernetes"],
        "keywords": ["backend", "api"],
    }
}

SAMPLE_PROFILE = {"name": "Saish"}
SAMPLE_SKILLS = ["Python", "Flask", "PostgreSQL", "AWS"]

SAMPLE_PROJECTS = [
    {
        "_id": "proj-a",
        "name": "Project A - Strong Match",
        "technologies": ["Python", "Flask", "PostgreSQL"],
        "keywords": ["backend", "api"],
        "categories": ["backend"],
        "description": "High alignment API project.",
        "resume_bullets": ["Created REST APIs using Python, Flask and PostgreSQL."],
    },
    {
        "_id": "proj-b",
        "name": "Project B - Medium Match",
        "technologies": ["Python", "Docker"],
        "keywords": ["backend"],
        "categories": ["backend"],
        "description": "Medium alignment project.",
        "resume_bullets": ["Deployed application in Docker."],
    },
    {
        "_id": "proj-c",
        "name": "Project C - Weak Match",
        "technologies": ["HTML", "CSS"],
        "keywords": ["frontend"],
        "categories": ["frontend"],
        "description": "Unrelated frontend work.",
        "resume_bullets": ["Built landing page styled with CSS."],
    },
]


def _make_mock_semantic_matcher(scores: dict[str, float]) -> MagicMock:
    """Return a mock SemanticMatcher returning custom scores for project names."""
    mock = MagicMock()

    def eval_side_effect(jd_data, project):
        name = project.get("name", "")
        # Find matching key
        score = 0.0
        for k, v in scores.items():
            if k in name:
                score = v
                break
        return ProjectSemanticMatch(
            relevance_score=score,
            matched_requirements=["Python"],
            supporting_evidence=["Found matching tech."],
            missing_requirements=[],
            reason=f"Mocked relevance score of {score}% assigned.",
        )

    mock.evaluate_project_relevance.side_effect = eval_side_effect
    return mock


class TestJDProfileMatcherPipeline:

    def test_end_to_end_orchestrator(self):
        # Setup mock semantic matcher with scores: Proj A = 95%, Proj B = 70%, Proj C = 20%
        mock_sem = _make_mock_semantic_matcher({
            "Strong": 95.0,
            "Medium": 70.0,
            "Weak": 20.0,
        })

        matcher = JDProfileMatcher(semantic_matcher=mock_sem)
        result = matcher.match(
            jd_document_id="test-jd-123",
            jd_data=SAMPLE_JD_DATA,
            profile_data=SAMPLE_PROFILE,
            skills=SAMPLE_SKILLS,
            projects=SAMPLE_PROJECTS,
        )

        assert isinstance(result, JobMatchResult)
        assert result.jd_document_id == "test-jd-123"
        assert result.job_title == "Backend Developer"

        # Required skills: Python, Flask, PostgreSQL matched (3/3) -> 100%
        assert result.required_skill_match_score == 100.0
        # Preferred skills: Docker, Kubernetes missing (0/2) -> 0%
        assert result.preferred_skill_match_score == 0.0

        # Project rankings check: A > B > C (Req 48)
        assert len(result.ranked_projects) == 3
        ranked = result.ranked_projects
        assert ranked[0].project_id == "proj-a"
        assert ranked[1].project_id == "proj-b"
        assert ranked[2].project_id == "proj-c"
        assert ranked[0].final_project_score > ranked[1].final_project_score
        assert ranked[1].final_project_score > ranked[2].final_project_score

        # Verify semantic evaluation was called on all candidates (limit is 5, we have 3)
        assert mock_sem.evaluate_project_relevance.call_count == 3

    def test_evaluate_all_projects_no_resume_limit(self):
        """REQUIRED TEST — ALL PROJECTS (Req 49)"""
        # Create 10 projects. The matcher must evaluate and return all 10.
        projects = []
        for i in range(10):
            projects.append({
                "_id": f"proj-{i}",
                "name": f"Project {i}",
                "technologies": ["Python"],
                "description": "Some project details.",
            })

        mock_sem = _make_mock_semantic_matcher({})
        matcher = JDProfileMatcher(semantic_matcher=mock_sem)

        result = matcher.match(
            jd_document_id="test-jd-123",
            jd_data=SAMPLE_JD_DATA,
            profile_data=SAMPLE_PROFILE,
            skills=SAMPLE_SKILLS,
            projects=projects,
        )

        # All 10 projects evaluated & returned
        assert len(result.ranked_projects) == 10
        # Semantic evaluation run only on top N (config.SEMANTIC_PROJECT_CANDIDATES = 5)
        assert mock_sem.evaluate_project_relevance.call_count == 5

    def test_dynamic_project_addition(self):
        """REQUIRED TEST — DYNAMIC PROJECT (Req 50)"""
        mock_sem = _make_mock_semantic_matcher({})
        matcher = JDProfileMatcher(semantic_matcher=mock_sem)

        # Start with 3 projects
        res1 = matcher.match(
            jd_document_id="test-jd-123",
            jd_data=SAMPLE_JD_DATA,
            profile_data=SAMPLE_PROFILE,
            skills=SAMPLE_SKILLS,
            projects=SAMPLE_PROJECTS,
        )
        assert len(res1.ranked_projects) == 3

        # Add project D dynamically to the input list
        projects_extended = list(SAMPLE_PROJECTS)
        projects_extended.append({
            "_id": "proj-d",
            "name": "Project D - New Dynamically Added Project",
            "technologies": ["Python"],
            "description": "Added dynamic project.",
        })

        # Match again
        res2 = matcher.match(
            jd_document_id="test-jd-123",
            jd_data=SAMPLE_JD_DATA,
            profile_data=SAMPLE_PROFILE,
            skills=SAMPLE_SKILLS,
            projects=projects_extended,
        )
        assert len(res2.ranked_projects) == 4
        assert any(p.project_id == "proj-d" for p in res2.ranked_projects)

    def test_no_project_match_graceful_scoring(self):
        """REQUIRED TEST — NO PROJECT MATCH (Req 51)"""
        # Projects completely unrelated to Python Backend Developer
        unrelated_projects = [
            {
                "_id": "u1",
                "name": "Gardening Blog",
                "technologies": ["Wordpress"],
                "description": "Gardening tips.",
            },
            {
                "_id": "u2",
                "name": "Furniture Store Site",
                "technologies": ["PHP", "MySQL"],
                "description": "Storefront page.",
            }
        ]

        mock_sem = _make_mock_semantic_matcher({
            "Gardening": 5.0,
            "Furniture": 10.0,
        })
        matcher = JDProfileMatcher(semantic_matcher=mock_sem)

        result = matcher.match(
            jd_document_id="test-jd-123",
            jd_data=SAMPLE_JD_DATA,
            profile_data=SAMPLE_PROFILE,
            skills=SAMPLE_SKILLS,
            projects=unrelated_projects,
        )

        assert len(result.ranked_projects) == 2
        # Verify scores are very low
        assert result.ranked_projects[0].final_project_score < 25.0
        assert result.ranked_projects[1].final_project_score < 25.0

    def test_missing_jd_fields_graceful_handling(self):
        """REQUIRED TEST — MISSING JD FIELDS (Req 52)"""
        # JD contains only required_skills, missing preferred, tech, keywords
        minimal_jd = {
            "analysis": {
                "job_title": "Developer",
                "required_skills": ["Python"],
                # missing preferred_skills, technologies, keywords, role_category
            }
        }

        mock_sem = _make_mock_semantic_matcher({})
        matcher = JDProfileMatcher(semantic_matcher=mock_sem)

        # Should not crash and successfully evaluate matching
        result = matcher.match(
            jd_document_id="test-jd-123",
            jd_data=minimal_jd,
            profile_data=SAMPLE_PROFILE,
            skills=SAMPLE_SKILLS,
            projects=SAMPLE_PROJECTS,
        )
        assert result.overall_match_score > 0
        assert result.required_skill_match_score == 100.0  # Python is in SAMPLE_SKILLS
        assert result.preferred_skill_match_score == 100.0  # absent -> 100%
        assert result.technology_match_score == 100.0  # absent -> 100%

    def test_empty_profile_graceful_handling(self):
        """REQUIRED TEST — EMPTY PROFILE (Req 53)"""
        mock_sem = _make_mock_semantic_matcher({})
        matcher = JDProfileMatcher(semantic_matcher=mock_sem)

        result = matcher.match(
            jd_document_id="test-jd-123",
            jd_data=SAMPLE_JD_DATA,
            profile_data={},
            skills=[],
            projects=[],
        )

        assert result.overall_match_score == 0.0
        assert result.required_skill_match_score == 0.0
        assert result.technology_match_score == 0.0
        assert result.ranked_projects == []

    def test_no_hallucinated_matches(self):
        """REQUIRED TEST — NO HALLUCINATED MATCHES (Req 56)"""
        # JD contains Kubernetes. Profile does not contain Kubernetes.
        # Project description/tech does not contain Kubernetes.
        # Matcher must report Kubernetes as missing and not matched.
        mock_sem = _make_mock_semantic_matcher({
            "Strong": 95.0,
        })
        matcher = JDProfileMatcher(semantic_matcher=mock_sem)

        result = matcher.match(
            jd_document_id="test-jd-123",
            jd_data=SAMPLE_JD_DATA,
            profile_data=SAMPLE_PROFILE,
            skills=["Python", "Flask", "PostgreSQL"],  # no Kubernetes or Docker
            projects=[SAMPLE_PROJECTS[0]],  # no Kubernetes or Docker
        )

        assert "Kubernetes" in result.missing_preferred_skills
        assert "Kubernetes" not in result.matched_preferred_skills
        assert "Kubernetes" in result.missing_technologies
        assert "Kubernetes" not in result.technologies if hasattr(result, "technologies") else True
        assert "Kubernetes" not in result.matched_technologies

    def test_all_projects_ranking_and_order(self):
        """Create or strengthen a test with at least 7 projects (Req 13)"""
        projects = []
        # Create 7 projects with distinct names to return different mock scores
        mock_scores = {}
        for i in range(7):
            name = f"ProjectRanked{i}"
            # Assign descending semantic scores: 95, 88, 74, 42, 20, 10, 5
            score_val = [95.0, 88.0, 74.0, 42.0, 20.0, 10.0, 5.0][i]
            mock_scores[name] = score_val
            projects.append({
                "_id": f"proj-{i}",
                "name": name,
                "technologies": ["Python"],
                "description": f"Description for project {i} containing Python.",
            })

        mock_sem = _make_mock_semantic_matcher(mock_scores)
        matcher = JDProfileMatcher(semantic_matcher=mock_sem)

        result = matcher.match(
            jd_document_id="test-jd-123",
            jd_data=SAMPLE_JD_DATA,
            profile_data=SAMPLE_PROFILE,
            skills=SAMPLE_SKILLS,
            projects=projects,
        )

        # 1. Verify all 7 projects are evaluated and present in ranked_projects
        assert len(result.ranked_projects) == 7

        # 2. Verify ranked_projects are sorted descending by final_project_score
        scores = [rp.final_project_score for rp in result.ranked_projects]
        assert scores == sorted(scores, reverse=True)

        # 3. Verify top 3 projects are used to calculate project_relevance_score
        # Scores are:
        # proj-0: prelim approx 23.7, semantic 95.0 -> final = 23.7*0.3 + 95*0.7 = 7.11 + 66.5 = 73.61 -> 73.6
        # proj-1: prelim approx 23.7, semantic 88.0 -> final = 23.7*0.3 + 88*0.7 = 7.11 + 61.6 = 68.71 -> 68.7
        # proj-2: prelim approx 23.7, semantic 74.0 -> final = 23.7*0.3 + 74*0.7 = 7.11 + 51.8 = 58.91 -> 58.9
        # Top 3 average should match result.project_relevance_score
        expected_avg = round((scores[0] + scores[1] + scores[2]) / 3.0, 1)
        assert result.project_relevance_score == expected_avg

