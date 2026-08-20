"""
test_scorer.py — Unit tests for the scorer engine.
"""

import pytest
from phase_3.matcher.scorer import calculate_project_final_score, calculate_overall_match_score
from phase_3.matcher.config import config


class TestScorer:

    def test_overall_weights_validation(self):
        # The active config must pass validation automatically on import
        assert abs(config.REQUIRED_SKILL_WEIGHT + config.PREFERRED_SKILL_WEIGHT + config.TECHNOLOGY_WEIGHT + config.PROJECT_WEIGHT - 1.0) < 1e-9

    def test_project_weights_validation(self):
        assert abs(config.PROJECT_REQUIRED_WEIGHT + config.PROJECT_PREFERRED_WEIGHT + config.PROJECT_TECHNOLOGY_WEIGHT + config.PROJECT_KEYWORD_WEIGHT + config.PROJECT_CATEGORY_WEIGHT - 1.0) < 1e-9

    def test_project_final_score_blending(self):
        # 1. No semantic score -> final = prelim
        assert calculate_project_final_score(80.0, None) == 80.0

        # 2. Combined blend: 30% prelim, 70% semantic
        # (80 * 0.3) + (90 * 0.7) = 24 + 63 = 87
        final = calculate_project_final_score(80.0, 90.0)
        assert final == 87.0

    def test_overall_match_score_calculation(self):
        # Required skills: 80% (weight 50%) -> 40 points
        # Preferred skills: 60% (weight 15%) -> 9 points
        # Technologies: 70% (weight 15%) -> 10.5 points
        # Projects: [90, 80, 70, 50] -> top 3 average = 80% (weight 20%) -> 16 points
        # Expected total = 40 + 9 + 10.5 + 16 = 75.5
        score = calculate_overall_match_score(
            required_score=80.0,
            preferred_score=60.0,
            tech_score=70.0,
            project_scores=[90.0, 80.0, 70.0, 50.0],
        )
        assert score == 75.5

    def test_overall_match_score_fewer_than_three_projects(self):
        # Projects: [90, 80] -> top average = 85% (weight 20%) -> 17 points
        # Required: 100% -> 50 points
        # Preferred: 100% -> 15 points
        # Tech: 100% -> 15 points
        # Expected = 50 + 15 + 15 + 17 = 97.0
        score = calculate_overall_match_score(
            required_score=100.0,
            preferred_score=100.0,
            tech_score=100.0,
            project_scores=[90.0, 80.0],
        )
        assert score == 97.0

    def test_overall_match_score_no_projects(self):
        # Projects empty -> project relevance = 0%
        # Req: 100% (50 points), Pref: 100% (15 points), Tech: 100% (15 points)
        # Expected = 80.0
        score = calculate_overall_match_score(
            required_score=100.0,
            preferred_score=100.0,
            tech_score=100.0,
            project_scores=[],
        )
        assert score == 80.0
