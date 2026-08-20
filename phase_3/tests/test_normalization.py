"""
test_normalization.py — Unit tests for skill name normalization.
"""

from phase_3.matcher.normalization import normalize_skill_name, normalize_skill_list


class TestNormalization:

    def test_alias_resolution(self):
        assert normalize_skill_name("React.js") == "React"
        assert normalize_skill_name("React JS") == "React"
        assert normalize_skill_name("reactjs") == "React"
        assert normalize_skill_name("amazon web services") == "AWS"
        assert normalize_skill_name("AWS") == "AWS"
        assert normalize_skill_name("Postgres") == "PostgreSQL"
        assert normalize_skill_name("postgresql") == "PostgreSQL"
        assert normalize_skill_name("RESTful API") == "REST API"

    def test_unrelated_technologies_not_merged(self):
        assert normalize_skill_name("Java") == "Java"
        assert normalize_skill_name("JavaScript") == "JavaScript"
        assert normalize_skill_name("Flask") == "Flask"
        assert normalize_skill_name("FastAPI") == "FastAPI"

    def test_case_insensitive_deduplication(self):
        input_list = ["Python", "python", "PYTHON", "AWS", "aws", "React", "ReactJS"]
        normalized = normalize_skill_list(input_list)
        # Deduplicated to Python, AWS, React
        assert normalized == ["Python", "AWS", "React"]

    def test_order_preservation(self):
        input_list = ["React JS", "Python", "AWS", "python"]
        normalized = normalize_skill_list(input_list)
        assert normalized == ["React", "Python", "AWS"]

    def test_empty_or_none_list_handling(self):
        assert normalize_skill_list([]) == []
        assert normalize_skill_list(None) == []
