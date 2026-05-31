"""Smoke tests for prompt construction - the agent must feed findings to the model."""

from __future__ import annotations

from analyzer.schema import Category, Finding, Severity
from agent.prompts import build_initial_prompt, build_repair_prompt


def _finding(line, ctype, *, semantic=False, cat=Category.SYNTAX, snippet="<x>", notes=None):
    return Finding(
        line=line, column=0, construct_type=ctype,
        category=cat, severity=Severity.WARNING,
        snippet=snippet, semantic_risk=semantic, notes=notes,
    )


def test_initial_prompt_surfaces_semantic_risk_section():
    findings = [
        _finding(5, "integer_division", semantic=True, cat=Category.SEMANTIC,
                 snippet="5 / 2",
                 notes="both operands are integer literals - definite int/int division"),
        _finding(10, "print_statement", snippet="print x"),
    ]
    prompt = build_initial_prompt("print x\n", findings)
    assert "SEMANTIC RISK" in prompt
    assert "integer_division" in prompt
    assert "definite int/int division" in prompt
    # Mechanical findings appear in a separate section.
    assert "MECHANICAL REWRITES" in prompt
    assert "print_statement" in prompt
    # And the original source is present.
    assert "print x" in prompt


def test_initial_prompt_handles_no_findings():
    prompt = build_initial_prompt("print('ok')\n", [])
    assert "No Py2 constructs were detected" in prompt
    assert "print('ok')" in prompt


def test_initial_prompt_only_semantic_findings():
    findings = [
        _finding(1, "dict_method_iteritems", semantic=True, cat=Category.SEMANTIC,
                 snippet="d.iteritems()",
                 notes="Py3 has no .iteritems"),
    ]
    prompt = build_initial_prompt("...", findings)
    assert "SEMANTIC RISK" in prompt
    # No mechanical section if there are no mechanical findings.
    assert "MECHANICAL REWRITES" not in prompt


def test_repair_prompt_carries_prior_code_and_tracebacks():
    findings = [_finding(1, "print_statement")]
    prompt = build_repair_prompt(
        source_py2="print x",
        findings=findings,
        prior_code="def bad():\n    return broken\n",
        recent_tracebacks=["test_a FAILED\nassert 1 == 2"],
        iteration=2,
    )
    assert "YOUR PREVIOUS MIGRATED CODE" in prompt
    assert "def bad():" in prompt
    assert "FAILING TEST OUTPUT" in prompt
    assert "assert 1 == 2" in prompt
    assert "repair iteration 2" in prompt


def test_stdlib_findings_get_their_own_section():
    findings = [
        _finding(1, "stdlib_rename_urllib2", cat=Category.STDLIB,
                 snippet="import urllib2",
                 notes="Py3: use urllib.request / urllib.error."),
    ]
    prompt = build_initial_prompt("import urllib2", findings)
    assert "STDLIB REORGANIZATION" in prompt
    assert "stdlib_rename_urllib2" in prompt
    assert "urllib.request" in prompt
