"""
test_content_tailor.py — Tests for Phase 4 content tailoring logic.

Covers:
  - Deterministic fallback (no Gemini)
  - Hallucination protection: fabricated skills rejected
  - Missing required skill NOT added to plan
  - Summary safety: only existing skills in focus
  - Gemini plan validation
"""

import pytest
from unittest.mock import MagicMock, patch
from phase_4.resume_tailor.content_tailor import ContentTailor
from phase_4.resume_tailor.schemas import TailoringPlan


class TestContentTailorDeterministic:
    """Tests for the deterministic fallback path (no Gemini)."""

    def _make_tailor_no_gemini(self) -> ContentTailor:
        tailor = ContentTailor.__new__(ContentTailor)
        tailor._api_key = ""
        tailor._model   = "test-model"
        tailor._client  = None
        return tailor

    def test_deterministic_plan_uses_phase3_matched_skills(
        self, mock_match_result, mock_skills_grouped, mock_ranked_projects
    ):
        """Deterministic plan emphasises Phase 3 matched required skills."""
        tailor = self._make_tailor_no_gemini()
        match  = {
            "matched_required_skills": ["Python", "Flask", "AWS"],
            "matched_technologies":    ["Python", "Flask"],
            "matched_preferred_skills": [],
            "missing_required_skills": ["Docker"],
        }
        ranked_ids = ["proj_a", "proj_b", "proj_c"]
        plan = tailor.plan(
            profile={},
            jd_data={},
            match_result=match,
            skills_grouped=mock_skills_grouped,
            ranked_project_ids=ranked_ids,
            all_projects_by_id={},
            project_limit=3,
        )
        assert isinstance(plan, TailoringPlan)
        assert "Python" in plan.skills_to_emphasize
        assert "Flask"  in plan.skills_to_emphasize
        assert "AWS"    in plan.skills_to_emphasize

    def test_deterministic_plan_project_ids_top_n(self, mock_skills_grouped):
        """Deterministic plan selects top-N project IDs from ranked list."""
        tailor = self._make_tailor_no_gemini()
        ranked_ids = ["proj_a", "proj_b", "proj_c", "proj_d", "proj_e"]
        plan = tailor.plan(
            profile={},
            jd_data={},
            match_result={
                "matched_required_skills": [],
                "matched_technologies": [],
                "matched_preferred_skills": [],
            },
            skills_grouped=mock_skills_grouped,
            ranked_project_ids=ranked_ids,
            all_projects_by_id={},
            project_limit=3,
        )
        assert plan.project_ids == ["proj_a", "proj_b", "proj_c"]
        assert "proj_d" not in plan.project_ids

    def test_missing_required_skill_not_added_to_plan(self, mock_skills_grouped):
        """
        Phase 3 reports Kubernetes as missing. The plan must NOT add Kubernetes
        to skills_to_emphasize if it's not in the profile.
        """
        tailor = self._make_tailor_no_gemini()
        match = {
            "matched_required_skills": ["Python"],
            "matched_technologies": [],
            "matched_preferred_skills": [],
            "missing_required_skills": ["Kubernetes"],
        }
        plan = tailor.plan(
            profile={},
            jd_data={},
            match_result=match,
            skills_grouped=mock_skills_grouped,
            ranked_project_ids=["proj_a"],
            all_projects_by_id={},
            project_limit=1,
        )
        assert "Kubernetes" not in plan.skills_to_emphasize


class TestContentTailorValidation:
    """Tests for the hallucination protection / validation layer."""

    def test_validate_plan_rejects_fabricated_skills(self, mock_skills_grouped):
        """Skills not in profile are removed from skills_to_emphasize."""
        tailor = ContentTailor.__new__(ContentTailor)
        tailor._api_key = "test"
        tailor._model   = "test"
        tailor._client  = MagicMock()

        # Simulated Gemini response with hallucinated skills
        raw_plan = TailoringPlan(
            summary_focus=["Python"],
            skills_to_emphasize=["Python", "Kubernetes", "FastAPI"],  # Kubernetes & FastAPI are fabricated
            project_ids=["proj_a"],
            tailoring_notes="Test plan.",
        )

        validated = tailor._validate_plan(
            plan=raw_plan,
            skills_grouped=mock_skills_grouped,
            ranked_project_ids=["proj_a", "proj_b", "proj_c"],
            project_limit=3,
        )

        assert "Python" in validated.skills_to_emphasize
        assert "Kubernetes" not in validated.skills_to_emphasize
        assert "FastAPI" not in validated.skills_to_emphasize

    def test_validate_plan_rejects_fabricated_summary_focus(self, mock_skills_grouped):
        """Skills in summary_focus not in profile are removed."""
        tailor = ContentTailor.__new__(ContentTailor)
        tailor._api_key = "test"
        tailor._model   = "test"
        tailor._client  = MagicMock()

        raw_plan = TailoringPlan(
            summary_focus=["Python", "Kubernetes"],  # Kubernetes not in profile
            skills_to_emphasize=[],
            project_ids=["proj_a"],
            tailoring_notes="",
        )

        validated = tailor._validate_plan(
            plan=raw_plan,
            skills_grouped=mock_skills_grouped,
            ranked_project_ids=["proj_a"],
            project_limit=3,
        )

        assert "Python" in validated.summary_focus
        assert "Kubernetes" not in validated.summary_focus

    def test_validate_plan_rejects_unknown_project_ids(self, mock_skills_grouped):
        """Project IDs not in Phase 3 ranked list are removed."""
        tailor = ContentTailor.__new__(ContentTailor)
        tailor._api_key = "test"
        tailor._model   = "test"
        tailor._client  = MagicMock()

        raw_plan = TailoringPlan(
            summary_focus=[],
            skills_to_emphasize=[],
            project_ids=["proj_a", "proj_invented_123"],  # proj_invented_123 is fake
            tailoring_notes="",
        )

        validated = tailor._validate_plan(
            plan=raw_plan,
            skills_grouped=mock_skills_grouped,
            ranked_project_ids=["proj_a", "proj_b", "proj_c"],
            project_limit=3,
        )

        assert "proj_a" in validated.project_ids
        assert "proj_invented_123" not in validated.project_ids

    def test_validate_fills_missing_project_ids(self, mock_skills_grouped):
        """
        If Gemini returns fewer project IDs than limit,
        the validator fills in top-ranked projects from Phase 3.
        """
        tailor = ContentTailor.__new__(ContentTailor)
        tailor._api_key = "test"
        tailor._model   = "test"
        tailor._client  = MagicMock()

        raw_plan = TailoringPlan(
            summary_focus=[],
            skills_to_emphasize=[],
            project_ids=["proj_a"],   # Gemini only chose 1, limit=3
            tailoring_notes="",
        )

        validated = tailor._validate_plan(
            plan=raw_plan,
            skills_grouped=mock_skills_grouped,
            ranked_project_ids=["proj_a", "proj_b", "proj_c"],
            project_limit=3,
        )

        assert len(validated.project_ids) == 3
        assert "proj_a" in validated.project_ids
        assert "proj_b" in validated.project_ids
        assert "proj_c" in validated.project_ids


class TestSummaryTailoring:
    """Tests for the summary tailoring helper."""

    def test_summary_unchanged_when_skills_already_mentioned(self):
        from phase_4.resume_tailor.resume_pipeline import _tailor_summary
        original = "Results-driven developer with Python and AWS experience."
        result = _tailor_summary(original, ["Python", "AWS"])
        assert result == original  # no modification needed

    def test_summary_extended_when_skill_missing(self):
        from phase_4.resume_tailor.resume_pipeline import _tailor_summary
        original = "Results-driven developer."
        result = _tailor_summary(original, ["Python"])
        assert "Python" in result
        assert original in result  # original is preserved

    def test_summary_no_fabrication_of_unsupported_tech(self):
        """Summary must not contain Kubernetes if not in focus list."""
        from phase_4.resume_tailor.resume_pipeline import _tailor_summary
        original = "Experienced backend developer."
        result = _tailor_summary(original, ["Python", "AWS"])
        assert "Kubernetes" not in result

    def test_empty_summary_handled_gracefully(self):
        from phase_4.resume_tailor.resume_pipeline import _tailor_summary
        result = _tailor_summary("", ["Python"])
        assert isinstance(result, str)

    def test_empty_focus_returns_original(self):
        from phase_4.resume_tailor.resume_pipeline import _tailor_summary
        original = "Original summary text."
        result = _tailor_summary(original, [])
        assert result == original
