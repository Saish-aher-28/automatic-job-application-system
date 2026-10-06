"""
test_project_selector.py — Tests for Phase 4 project selection logic.
"""

import pytest
from phase_4.resume_tailor.project_selector import (
    select_projects,
    build_projects_by_id_map,
)


class TestSelectProjects:

    def test_top_three_selected_by_default(self, mock_projects, mock_ranked_projects):
        """Top-3 projects by Phase 3 score are selected when limit=3."""
        projects_by_id = build_projects_by_id_map(mock_projects)
        selected = select_projects(
            ranked_projects=mock_ranked_projects,
            all_projects_by_id=projects_by_id,
            required_technologies=["Python", "AWS", "Flask"],
            limit=3,
        )
        assert len(selected) == 3
        assert selected[0] == "proj_a"   # highest Phase 3 score
        assert selected[1] == "proj_b"   # second highest
        assert "proj_d" not in selected  # frontend project, low score

    def test_limit_one(self, mock_projects, mock_ranked_projects):
        """Only the top project is selected when limit=1."""
        projects_by_id = build_projects_by_id_map(mock_projects)
        selected = select_projects(
            ranked_projects=mock_ranked_projects,
            all_projects_by_id=projects_by_id,
            required_technologies=[],
            limit=1,
        )
        assert len(selected) == 1
        assert selected[0] == "proj_a"

    def test_empty_ranked_projects_returns_empty(self, mock_projects):
        """Empty ranked list returns empty selection."""
        projects_by_id = build_projects_by_id_map(mock_projects)
        selected = select_projects(
            ranked_projects=[],
            all_projects_by_id=projects_by_id,
            required_technologies=["Python"],
            limit=3,
        )
        assert selected == []

    def test_fewer_projects_than_limit(self, mock_projects, mock_ranked_projects):
        """If only 2 projects are ranked, select at most 2 even if limit=5."""
        projects_by_id = build_projects_by_id_map(mock_projects)
        only_two = mock_ranked_projects[:2]
        selected = select_projects(
            ranked_projects=only_two,
            all_projects_by_id=projects_by_id,
            required_technologies=["Python"],
            limit=5,
        )
        assert len(selected) == 2

    def test_coverage_diversity_swap(self, mock_projects, mock_ranked_projects):
        """
        A lower-ranked project covering an otherwise-uncovered required technology
        may be swapped in for the lowest-ranked selected project.

        Scenario:
          top-3 by Phase 3: proj_a (AWS, Python), proj_b (Python, Flask), proj_c (Python)
          Required tech includes "React" (only in proj_d).
          proj_d should swap in for proj_c (lowest in top-3).
        """
        projects_by_id = build_projects_by_id_map(mock_projects)

        # Required tech includes React which only proj_d has
        selected = select_projects(
            ranked_projects=mock_ranked_projects,
            all_projects_by_id=projects_by_id,
            required_technologies=["Python", "AWS", "React"],
            limit=3,
        )
        # proj_d should replace proj_c (the lowest-ranked of the top-3)
        assert "proj_d" in selected
        assert "proj_c" not in selected
        assert "proj_a" in selected   # top 2 should remain
        assert "proj_b" in selected

    def test_no_swap_when_full_coverage(self, mock_projects, mock_ranked_projects):
        """No swap when the top-3 already cover all required technologies."""
        projects_by_id = build_projects_by_id_map(mock_projects)
        selected = select_projects(
            ranked_projects=mock_ranked_projects,
            all_projects_by_id=projects_by_id,
            required_technologies=["Python"],  # all top-3 have Python
            limit=3,
        )
        # Phase 3 order preserved, no swap
        assert selected[:3] == ["proj_a", "proj_b", "proj_c"]

    def test_dynamic_new_project_can_be_selected(self, mock_projects, mock_ranked_projects):
        """
        A newly added project that ranks high in Phase 3 is automatically selected.
        No code change required — the system is fully dynamic.
        """
        # Inject a new project into the system
        new_project = {
            "_id": "proj_new",
            "name": "New AI Platform",
            "technologies": ["Python", "Docker", "Kubernetes"],
            "keywords": ["cloud", "devops"],
            "enabled": True,
        }
        extended_projects = mock_projects + [new_project]
        projects_by_id = build_projects_by_id_map(extended_projects)

        # Add new project at the top of Phase 3 ranking
        new_ranked = [
            {
                "project_id": "proj_new",
                "project_name": "New AI Platform",
                "preliminary_score": 99.0,
                "semantic_score": 99.0,
                "final_project_score": 99.0,
                "matched_skills": ["Python", "Docker"],
                "matched_technologies": ["Python", "Docker", "Kubernetes"],
                "missing_relevant_skills": [],
                "reason": "Perfect match.",
            }
        ] + mock_ranked_projects

        selected = select_projects(
            ranked_projects=new_ranked,
            all_projects_by_id=projects_by_id,
            required_technologies=["Python", "Docker"],
            limit=3,
        )
        # New project must be selected (highest score)
        assert "proj_new" in selected
        assert selected[0] == "proj_new"

    def test_build_projects_by_id_map(self, mock_projects):
        """build_projects_by_id_map correctly indexes projects by _id."""
        projects_by_id = build_projects_by_id_map(mock_projects)
        assert len(projects_by_id) == len(mock_projects)
        for proj in mock_projects:
            assert proj["_id"] in projects_by_id
            assert projects_by_id[proj["_id"]]["name"] == proj["name"]
