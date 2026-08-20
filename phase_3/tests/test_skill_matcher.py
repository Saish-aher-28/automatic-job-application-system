"""
test_skill_matcher.py — Unit tests for deterministic skill and technology matching.
"""

from phase_3.matcher.skill_matcher import calculate_match_details, match_skills_and_technologies


class TestSkillMatcher:

    def test_perfect_match(self):
        """REQUIRED TEST — PERFECT MATCH (Req 43)"""
        jd_required = ["Python", "Flask", "AWS"]
        profile_skills = ["Python", "Flask", "AWS"]
        matched, missing, score = calculate_match_details(jd_required, profile_skills)
        assert score == 100.0
        assert matched == ["Python", "Flask", "AWS"]
        assert missing == []

    def test_zero_match(self):
        """REQUIRED TEST — ZERO MATCH (Req 44)"""
        jd_required = ["Kotlin", "Android", "Jetpack Compose"]
        profile_skills = ["Python", "Flask", "AWS"]
        matched, missing, score = calculate_match_details(jd_required, profile_skills)
        assert score == 0.0
        assert matched == []
        assert missing == ["Kotlin", "Android", "Jetpack Compose"]

    def test_partial_match(self):
        """REQUIRED TEST — PARTIAL MATCH (Req 45)"""
        jd_required = ["Python", "Flask", "AWS", "Docker"]
        profile_skills = ["Python", "Flask", "AWS"]
        matched, missing, score = calculate_match_details(jd_required, profile_skills)
        assert score == 75.0
        assert matched == ["Python", "Flask", "AWS"]
        assert missing == ["Docker"]

    def test_required_and_preferred_skills(self):
        """REQUIRED TEST — PREFERRED SKILLS (Req 46)"""
        jd_required = ["Python", "AWS"]
        jd_preferred = ["Docker", "Kubernetes"]
        profile_skills = ["Python", "AWS", "Docker"]

        res = match_skills_and_technologies(
            jd_required=jd_required,
            jd_preferred=jd_preferred,
            jd_technologies=[],
            user_skills=profile_skills,
            user_project_technologies=[],
        )

        assert res["required_skill_match_score"] == 100.0
        assert res["preferred_skill_match_score"] == 50.0
        assert res["matched_required_skills"] == ["Python", "AWS"]
        assert res["missing_required_skills"] == []
        assert res["matched_preferred_skills"] == ["Docker"]
        assert res["missing_preferred_skills"] == ["Kubernetes"]

    def test_normalization_integration(self):
        """REQUIRED TEST — NORMALIZATION (Req 47)"""
        jd_required = ["Amazon Web Services", "React.js", "RESTful APIs"]
        profile_skills = ["AWS", "React", "REST API"]
        matched, missing, score = calculate_match_details(jd_required, profile_skills)
        assert score == 100.0
        assert len(matched) == 3
        assert missing == []

    def test_technology_matching_with_project_tech(self):
        """Technologies check matches against BOTH profile skills and project tech."""
        jd_tech = ["Python", "Docker", "XGBoost", "PostgreSQL"]
        profile_skills = ["Python"]
        project_techs = ["Docker", "XGBoost"]  # not in profile skills

        res = match_skills_and_technologies(
            jd_required=[],
            jd_preferred=[],
            jd_technologies=jd_tech,
            user_skills=profile_skills,
            user_project_technologies=project_techs,
        )

        assert res["technology_match_score"] == 75.0
        assert set(res["matched_technologies"]) == {"Python", "Docker", "XGBoost"}
        assert res["missing_technologies"] == ["PostgreSQL"]

    def test_empty_jd_requirements(self):
        """If JD requires nothing, score defaults to 100.0 (Req 52)."""
        res = match_skills_and_technologies(
            jd_required=[],
            jd_preferred=[],
            jd_technologies=[],
            user_skills=["Python"],
            user_project_technologies=[],
        )
        assert res["required_skill_match_score"] == 100.0
        assert res["preferred_skill_match_score"] == 100.0
        assert res["technology_match_score"] == 100.0

    def test_empty_profile(self):
        """If profile has no skills/tech, match is 0.0 (Req 53)."""
        res = match_skills_and_technologies(
            jd_required=["Python"],
            jd_preferred=["Docker"],
            jd_technologies=["Python", "Docker"],
            user_skills=[],
            user_project_technologies=[],
        )
        assert res["required_skill_match_score"] == 0.0
        assert res["preferred_skill_match_score"] == 0.0
        assert res["technology_match_score"] == 0.0
        assert res["missing_required_skills"] == ["Python"]
        assert res["missing_preferred_skills"] == ["Docker"]
