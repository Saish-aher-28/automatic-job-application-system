"""
test_validators.py — Unit tests for LaTeX escaping and field validation.

These tests require NO Firestore connection.
"""

import pytest
from resume_engine.validators import (
    latex_escape,
    latex_escape_list,
    validate_project,
    validate_profile,
    validate_certification,
    validate_education,
    coerce_list,
    extract_username_from_url,
)


# ────────────────────────────────────────────────────────────────────
# LaTeX Escaping Tests
# ────────────────────────────────────────────────────────────────────

class TestLatexEscape:

    def test_ampersand(self):
        assert latex_escape("R&D") == r"R\&D"

    def test_percent(self):
        assert latex_escape("50%") == r"50\%"

    def test_dollar(self):
        assert latex_escape("$100") == r"\$100"

    def test_hash(self):
        assert latex_escape("#1") == r"\#1"

    def test_underscore(self):
        assert latex_escape("user_name") == r"user\_name"

    def test_curly_open(self):
        assert latex_escape("a{b") == r"a\{b"

    def test_curly_close(self):
        assert latex_escape("a}b") == r"a\}b"

    def test_backslash(self):
        result = latex_escape("a\\b")
        assert "textbackslash" in result

    def test_caret(self):
        result = latex_escape("a^b")
        assert "textasciicircum" in result

    def test_tilde(self):
        result = latex_escape("a~b")
        assert "textasciitilde" in result

    def test_cpp(self):
        # C++ has no special chars — should remain unchanged
        assert latex_escape("C++") == "C++"

    def test_python(self):
        assert latex_escape("Python") == "Python"

    def test_mixed(self):
        # R&D with 50%
        result = latex_escape("R&D 50%")
        assert r"\&" in result
        assert r"\%" in result

    def test_empty_string(self):
        assert latex_escape("") == ""

    def test_non_string_coerced(self):
        # Should not raise
        result = latex_escape(42)
        assert result == "42"

    def test_all_safe_chars(self):
        # These should pass through unchanged
        safe = "Hello World! Python 3.11 (latest)"
        assert latex_escape(safe) == safe

    def test_url_like_string(self):
        # Dollar sign in a URL-like string
        result = latex_escape("price is $100 USD")
        assert r"\$" in result

    def test_latex_escape_list(self):
        items = ["R&D", "50%", "Python"]
        escaped = latex_escape_list(items)
        assert escaped[0] == r"R\&D"
        assert escaped[1] == r"50\%"
        assert escaped[2] == "Python"

    def test_backslash_not_double_escaped(self):
        """Backslash should only be escaped once."""
        result = latex_escape("a\\b")
        # Should contain exactly one textbackslash{}, not two
        assert result.count("textbackslash") == 1


# ────────────────────────────────────────────────────────────────────
# Project Validation Tests
# ────────────────────────────────────────────────────────────────────

class TestValidateProject:

    def test_valid_project(self):
        data = {
            "name": "MyProject",
            "description": "A great project",
            "technologies": ["Python", "Flask"],
        }
        assert validate_project(data) == []

    def test_missing_name(self):
        data = {"description": "desc", "technologies": ["Python"]}
        errors = validate_project(data)
        assert any("name" in e for e in errors)

    def test_missing_description(self):
        data = {"name": "proj", "technologies": ["Python"]}
        errors = validate_project(data)
        assert any("description" in e for e in errors)

    def test_missing_technologies(self):
        data = {"name": "proj", "description": "desc"}
        errors = validate_project(data)
        assert any("technologies" in e for e in errors)

    def test_technologies_not_list(self):
        data = {"name": "p", "description": "d", "technologies": "Python"}
        errors = validate_project(data)
        assert any("list" in e for e in errors)

    def test_enabled_must_be_bool(self):
        data = {
            "name": "p", "description": "d",
            "technologies": ["Python"],
            "enabled": "yes",
        }
        errors = validate_project(data)
        assert any("boolean" in e for e in errors)

    def test_empty_name_fails(self):
        data = {"name": "", "description": "desc", "technologies": []}
        errors = validate_project(data)
        assert any("name" in e for e in errors)


# ────────────────────────────────────────────────────────────────────
# Profile Validation Tests
# ────────────────────────────────────────────────────────────────────

class TestValidateProfile:

    def test_valid_profile(self):
        data = {"name": "John Doe", "email": "john@example.com"}
        assert validate_profile(data) == []

    def test_missing_name(self):
        errors = validate_profile({"email": "a@b.com"})
        assert any("name" in e for e in errors)

    def test_missing_email(self):
        errors = validate_profile({"name": "John"})
        assert any("email" in e for e in errors)


# ────────────────────────────────────────────────────────────────────
# Utility Tests
# ────────────────────────────────────────────────────────────────────

class TestCoerceList:

    def test_none_returns_empty(self):
        assert coerce_list(None) == []

    def test_list_passthrough(self):
        assert coerce_list(["a", "b"]) == ["a", "b"]

    def test_string_wrapped(self):
        assert coerce_list("hello") == ["hello"]


class TestExtractUsername:

    def test_linkedin_full_url(self):
        url = "https://linkedin.com/in/johndoe"
        assert extract_username_from_url(url, "linkedin") == "johndoe"

    def test_linkedin_with_trailing_slash(self):
        url = "https://linkedin.com/in/johndoe/"
        assert extract_username_from_url(url, "linkedin") == "johndoe"

    def test_github_full_url(self):
        url = "https://github.com/johndoe"
        assert extract_username_from_url(url, "github") == "johndoe"

    def test_plain_username(self):
        # If just a username is stored, return it as-is
        assert extract_username_from_url("johndoe", "github") == "johndoe"

    def test_empty_url(self):
        assert extract_username_from_url("", "github") == ""
