"""
test_skill_selector.py — Tests for Phase 4 skill reordering logic.
"""

import pytest
from phase_4.resume_tailor.skill_selector import reorder_skills, get_actually_emphasized


class TestReorderSkills:

    def test_emphasized_skills_move_to_front(self, mock_skills_grouped):
        """Skills to emphasize are placed at the front of their category."""
        reordered = reorder_skills(
            skills_grouped=mock_skills_grouped,
            skills_to_emphasize=["AWS", "Docker"],
        )
        # AWS and Docker are in 'Other'
        other_skills = reordered["Other"]
        assert other_skills[0] == "AWS"
        assert other_skills[1] == "Docker"

    def test_no_skills_added(self, mock_skills_grouped):
        """Reordering never increases the total number of skills."""
        original_count = sum(len(v) for v in mock_skills_grouped.values())
        reordered = reorder_skills(
            skills_grouped=mock_skills_grouped,
            skills_to_emphasize=["Python", "AWS"],
        )
        reordered_count = sum(len(v) for v in reordered.values())
        assert reordered_count == original_count

    def test_no_skills_removed(self, mock_skills_grouped):
        """All original skills are preserved after reordering."""
        original_skills = sorted([s for lst in mock_skills_grouped.values() for s in lst])
        reordered = reorder_skills(
            skills_grouped=mock_skills_grouped,
            skills_to_emphasize=["Python", "Flask"],
        )
        reordered_skills = sorted([s for lst in reordered.values() for s in lst])
        assert reordered_skills == original_skills

    def test_nonexistent_skill_silently_ignored(self, mock_skills_grouped):
        """Skills not in the profile are silently ignored without error."""
        reordered = reorder_skills(
            skills_grouped=mock_skills_grouped,
            skills_to_emphasize=["Kubernetes", "Rust"],  # neither in profile
        )
        # Content unchanged since no valid skills to move
        original_count = sum(len(v) for v in mock_skills_grouped.values())
        reordered_count = sum(len(v) for v in reordered.values())
        assert reordered_count == original_count

    def test_empty_emphasis_no_change(self, mock_skills_grouped):
        """Empty skills_to_emphasize returns skills in original order."""
        reordered = reorder_skills(
            skills_grouped=mock_skills_grouped,
            skills_to_emphasize=[],
        )
        for cat in mock_skills_grouped:
            assert reordered[cat] == mock_skills_grouped[cat]

    def test_category_order_preserved(self, mock_skills_grouped):
        """Category keys are preserved in the returned dict."""
        reordered = reorder_skills(
            skills_grouped=mock_skills_grouped,
            skills_to_emphasize=["Python"],
        )
        assert list(reordered.keys()) == list(mock_skills_grouped.keys())

    def test_multiple_categories_emphasize(self, mock_skills_grouped):
        """Emphasizing skills from multiple categories works correctly."""
        reordered = reorder_skills(
            skills_grouped=mock_skills_grouped,
            skills_to_emphasize=["Python", "AWS", "Flask"],
        )
        # Python is in Programming Languages
        assert reordered["Programming Languages"][0] == "Python"
        # Flask is in Web Development
        assert reordered["Web Development"][0] == "Flask"
        # AWS is in Other
        assert reordered["Other"][0] == "AWS"

    def test_case_insensitive_matching(self, mock_skills_grouped):
        """Skill matching is case-insensitive."""
        reordered = reorder_skills(
            skills_grouped=mock_skills_grouped,
            skills_to_emphasize=["python", "aws"],  # lowercase
        )
        # Python should move to front of Programming Languages
        assert reordered["Programming Languages"][0] == "Python"
        # AWS should move to front of Other
        assert reordered["Other"][0] == "AWS"

    def test_get_actually_emphasized_filters_nonexistent(self, mock_skills_grouped):
        """get_actually_emphasized returns only skills that exist in profile."""
        result = get_actually_emphasized(
            skills_grouped=mock_skills_grouped,
            skills_to_emphasize=["Python", "Kubernetes", "AWS", "Rust"],
        )
        assert "Python" in result
        assert "AWS" in result
        assert "Kubernetes" not in result
        assert "Rust" not in result

    def test_get_actually_emphasized_empty_input(self, mock_skills_grouped):
        """get_actually_emphasized returns empty list for empty input."""
        result = get_actually_emphasized(mock_skills_grouped, [])
        assert result == []
