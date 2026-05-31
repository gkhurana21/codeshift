"""Smoke tests for agent.parsing - the defensive output parser."""

from __future__ import annotations

from agent.parsing import parse_model_output, strip_fences_and_prose


def test_clean_code_passes_through():
    raw = "def foo():\n    return 1\n"
    out = parse_model_output(raw)
    assert out.ok
    assert "def foo()" in out.code


def test_strips_python_fence():
    raw = "```python\ndef foo():\n    return 1\n```"
    out = parse_model_output(raw)
    assert out.ok, out.parse_error
    assert "def foo()" in out.code
    assert "```" not in out.code


def test_strips_bare_fence():
    raw = "```\ndef foo():\n    return 1\n```"
    out = parse_model_output(raw)
    assert out.ok
    assert "```" not in out.code


def test_strips_prose_intro_line():
    raw = (
        "Here is the migrated code:\n"
        "def foo():\n"
        "    return 1\n"
    )
    out = parse_model_output(raw)
    assert out.ok
    assert out.code.startswith("def foo()")


def test_strips_prose_then_fence():
    raw = (
        "Here you go:\n"
        "```python\n"
        "def foo():\n"
        "    return 1\n"
        "```\n"
        "Let me know if you need changes."
    )
    out = parse_model_output(raw)
    assert out.ok, out.parse_error
    assert out.code.startswith("def foo()")
    assert "Let me know" not in out.code


def test_invalid_python_returns_parse_error():
    raw = "def foo(:\n    return 1\n"
    out = parse_model_output(raw)
    assert not out.ok
    assert "SyntaxError" in (out.parse_error or "")


def test_strip_does_not_swallow_real_function_def_with_colon():
    """Regression: a function def ending in `:` must not be treated as prose."""
    raw = (
        "def foo(x):\n"
        "    return x + 1\n"
    )
    s = strip_fences_and_prose(raw)
    assert s.startswith("def foo(x):")


def test_empty_response_does_not_crash():
    out = parse_model_output("")
    assert not out.ok or out.code.strip() == ""
