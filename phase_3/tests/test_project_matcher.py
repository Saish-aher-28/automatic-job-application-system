"""
test_project_matcher.py — Unit tests for Stage 1 project deterministic scoring.
"""

from phase_3.matcher.project_matcher import calculate_project_preliminary_score


class TestProjectMatcher:

    def test_strong_matching_project(self):
        project = {
            "name": "CloudReport Pipeline",
            "technologies": ["AWS", "Python", "Lambda", "S3"],
            "keywords": ["reporting", "pipeline", "backend"],
            "categories": ["cloud", "backend"],
            "description": "Built a serverless reporting system on AWS.",
            "resume_bullets": ["Deployed Lambda functions for data processing."],
        }

        jd_required = ["Python", "AWS"]
        jd_preferred = ["Lambda"]
        jd_tech = ["AWS", "Python", "Docker"]  # Docker is missing
        jd_kws = ["backend"]
        jd_role_category = "Backend"

        res = calculate_project_preliminary_score(
            project=project,
            jd_required=jd_required,
            jd_preferred=jd_preferred,
            jd_technologies=jd_tech,
            jd_keywords=jd_kws,
            jd_role_category=jd_role_category,
        )

        # Let's verify scores individually
        # Required: Python, AWS are both matched -> 100% (weight 40%) -> 40 points
        # Preferred: Lambda is matched -> 100% (weight 15%) -> 15 points
        # Technologies: AWS, Python matched, Docker missing -> 2/3 = 66.67% (weight 20%) -> 13.33 points
        # Keywords: backend is matched -> 100% (weight 15%) -> 15 points
        # Category: role_category "Backend" matched -> 100% (weight 10%) -> 10 points
        # Total score ~ 40 + 15 + 13.33 + 15 + 10 = 93.3%
        assert res["preliminary_score"] > 90.0
        assert res["preliminary_score"] < 95.0
        assert set(res["matched_skills"]) == {"Python", "AWS", "Lambda"}
        assert set(res["matched_technologies"]) == {"AWS", "Python"}
        assert res["missing_relevant_skills"] == []

    def test_weak_matching_project(self):
        project = {
            "name": "Simple HTML Site",
            "technologies": ["HTML", "CSS"],
            "keywords": ["static", "website"],
            "categories": ["frontend"],
            "description": "Created a simple static homepage.",
            "resume_bullets": ["Styled layout using basic CSS."],
        }

        jd_required = ["Python", "AWS"]
        jd_preferred = ["Docker"]
        jd_tech = ["Python", "AWS", "PostgreSQL"]
        jd_kws = ["cloud"]
        jd_role_category = "Backend"

        res = calculate_project_preliminary_score(
            project=project,
            jd_required=jd_required,
            jd_preferred=jd_preferred,
            jd_technologies=jd_tech,
            jd_keywords=jd_kws,
            jd_role_category=jd_role_category,
        )

        # Match should be 0.0 (except category/empty defaults if any - none matched)
        # Required: 0/2 = 0% -> 0 pts
        # Preferred: 0/1 = 0% -> 0 pts
        # Technologies: 0/3 = 0% -> 0 pts
        # Keywords: 0/1 = 0% -> 0 pts
        # Category: "Backend" not matched -> 0% -> 0 pts
        # Score = 0
        assert res["preliminary_score"] == 0.0
        assert res["matched_skills"] == []
        assert res["matched_technologies"] == []
        assert set(res["missing_relevant_skills"]) == {"Python", "AWS", "Docker"}

    def test_empty_jd_fallback_in_project_matching(self):
        """If JD lists no requirements, preliminary score defaults to 100.0."""
        project = {"name": "Empty Project"}
        res = calculate_project_preliminary_score(
            project=project,
            jd_required=[],
            jd_preferred=[],
            jd_technologies=[],
            jd_keywords=[],
            jd_role_category=None,
        )
        assert res["preliminary_score"] == 100.0
