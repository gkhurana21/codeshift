"""Smoke tests for the Phase 1 analyzer.

These tests pin behavior we care about: each detector finds what it should,
nothing more, and the analyzer never crashes on gnarly Py2 input.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from analyzer import analyze_source
from analyzer.schema import Category, Severity


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def types(report) -> set[str]:
    return {f.construct_type for f in report.findings}


def find(report, construct_type: str):
    return [f for f in report.findings if f.construct_type == construct_type]


# --- Doesn't crash on gnarly input (acceptance criterion) --------------------

def test_does_not_crash_on_gnarly_py2():
    sample = PROJECT_ROOT / "samples" / "gnarly_py2.py"
    report = analyze_source(sample.read_text(), path=str(sample))
    assert report.findings, "expected at least one finding"


def test_gnarly_sample_hits_every_category():
    sample = PROJECT_ROOT / "samples" / "gnarly_py2.py"
    report = analyze_source(sample.read_text(), path=str(sample))
    cats = {f.category for f in report.findings}
    assert {Category.SYNTAX, Category.SEMANTIC, Category.STDLIB, Category.META} <= cats


def test_gnarly_sample_marks_semantic_risk_distinctly():
    sample = PROJECT_ROOT / "samples" / "gnarly_py2.py"
    report = analyze_source(sample.read_text(), path=str(sample))
    semantic = [f for f in report.findings if f.semantic_risk]
    non_semantic = [f for f in report.findings if not f.semantic_risk]
    assert semantic and non_semantic
    # All semantic-risk findings should be in the semantic category.
    assert all(f.category == Category.SEMANTIC for f in semantic)


# --- Print statement vs print function ---------------------------------------

def test_print_statement_flagged():
    r = analyze_source("print 'hi'\n")
    assert "print_statement" in types(r)


def test_print_function_not_flagged():
    r = analyze_source("print('hi')\n")
    assert "print_statement" not in types(r)


def test_print_redirect_flagged():
    r = analyze_source("import sys\nprint >> sys.stderr, 'oops'\n")
    assert "print_statement" in types(r)


# --- Except / raise comma forms ----------------------------------------------

def test_old_except_flagged():
    r = analyze_source("try:\n    pass\nexcept IOError, e:\n    pass\n")
    fs = find(r, "except_comma")
    assert fs and fs[0].severity == Severity.ERROR


def test_new_except_not_flagged():
    r = analyze_source("try:\n    pass\nexcept IOError as e:\n    pass\n")
    assert "except_comma" not in types(r)


def test_old_raise_flagged():
    r = analyze_source("raise IOError, 'bad'\n")
    assert "raise_comma" in types(r)


def test_new_raise_not_flagged():
    r = analyze_source("raise IOError('bad')\n")
    assert "raise_comma" not in types(r)


# --- Tuple-unpacking params --------------------------------------------------

def test_tuple_params_flagged():
    r = analyze_source("def f((a, b)):\n    return a + b\n")
    assert "tuple_param" in types(r)


def test_normal_params_not_flagged():
    r = analyze_source("def f(a, b):\n    return a + b\n")
    assert "tuple_param" not in types(r)


# --- exec / backtick / <> ----------------------------------------------------

def test_exec_statement_flagged():
    r = analyze_source("exec 'x = 1'\n")
    assert "exec_statement" in types(r)


def test_exec_function_not_flagged():
    r = analyze_source("exec('x = 1')\n")
    assert "exec_statement" not in types(r)


def test_backtick_repr_flagged():
    r = analyze_source("y = `123`\n")
    assert "backtick_repr" in types(r)


def test_ne_operator_via_tokens():
    r = analyze_source("if 1 <> 2:\n    pass\n")
    assert "ne_operator" in types(r)


def test_ne_inside_string_not_flagged():
    r = analyze_source("s = '<>'\n")
    assert "ne_operator" not in types(r)


# --- Numeric literals --------------------------------------------------------

def test_old_octal_flagged():
    r = analyze_source("mode = 0755\n")
    assert "old_octal_literal" in types(r)


def test_new_octal_not_flagged():
    r = analyze_source("mode = 0o755\n")
    assert "old_octal_literal" not in types(r)


def test_zero_not_flagged_as_octal():
    r = analyze_source("x = 0\n")
    assert "old_octal_literal" not in types(r)


def test_long_literal_flagged():
    r = analyze_source("big = 10L\n")
    assert "long_literal" in types(r)


# --- Integer division -------------------------------------------------------

def test_int_div_literals_flagged_high_confidence():
    r = analyze_source("x = 5 / 2\n")
    fs = find(r, "integer_division")
    assert fs and "definite" in (fs[0].notes or "")
    assert fs[0].severity == Severity.WARNING


def test_int_div_with_vars_flagged_low_confidence():
    r = analyze_source("def avg(a, b):\n    return (a + b) / 2\n")
    fs = find(r, "integer_division")
    assert fs
    # heuristic: severity should be INFO when operand types are unknown
    assert fs[0].severity == Severity.INFO


def test_future_division_neutralizes_int_div():
    r = analyze_source("from __future__ import division\nx = 5 / 2\n")
    assert "integer_division" not in types(r)
    assert "division" in r.future_flags


def test_floor_div_not_flagged():
    r = analyze_source("x = 5 // 2\n")
    assert "integer_division" not in types(r)


# --- Dict methods / removed builtins ----------------------------------------

def test_dict_methods_flagged():
    src = (
        "d = {'a': 1}\n"
        "for k in d.iterkeys(): pass\n"
        "if d.has_key('a'): pass\n"
        "list(d.iteritems())\n"
        "list(d.itervalues())\n"
    )
    r = analyze_source(src)
    t = types(r)
    assert {"dict_method_iterkeys", "dict_method_has_key", "dict_method_iteritems", "dict_method_itervalues"} <= t


def test_iterator_next_method_flagged():
    r = analyze_source("it = iter([1])\nit.next()\n")
    assert "iterator_next_method" in types(r)


def test_removed_builtin_xrange_flagged():
    r = analyze_source("for i in xrange(10): pass\n")
    assert "removed_builtin_xrange" in types(r)


def test_removed_builtin_basestring_as_name_flagged():
    r = analyze_source("if isinstance(x, basestring): pass\n")
    assert "removed_builtin_name_basestring" in types(r)


def test_cmp_kwarg_name_not_flagged_as_builtin():
    """Regression: `sorted(xs, cmp=...)` should NOT flag 'cmp' as a builtin reference."""
    r = analyze_source("sorted(xs, cmp=lambda a,b: -1)\n")
    # The kwarg name 'cmp' is part of the sorted_cmp_kwarg finding, not a builtin reference.
    assert "removed_builtin_name_cmp" not in types(r)
    assert "sorted_cmp_kwarg" in types(r)


# --- Stdlib renames ---------------------------------------------------------

@pytest.mark.parametrize("src,expected", [
    ("import urllib2\n", "stdlib_rename_urllib2"),
    ("from StringIO import StringIO\n", "stdlib_rename_StringIO"),
    ("import ConfigParser\n", "stdlib_rename_ConfigParser"),
    ("import Queue\n", "stdlib_rename_Queue"),
    ("import cPickle\n", "stdlib_rename_cPickle"),
])
def test_stdlib_renames(src, expected):
    r = analyze_source(src)
    assert expected in types(r)


# --- map/filter/zip semantic risk -------------------------------------------

def test_len_of_map_flagged():
    r = analyze_source("n = len(map(int, xs))\n")
    assert "iter_builtin_len_map" in types(r)


def test_indexing_filter_flagged():
    r = analyze_source("first = filter(None, xs)[0]\n")
    assert "iter_builtin_index_filter" in types(r)


def test_plain_map_not_flagged_as_misuse():
    r = analyze_source("ys = map(int, xs)\n")  # plain assignment is fine
    assert "iter_builtin_len_map" not in types(r)
    assert "iter_builtin_index_map" not in types(r)


# --- Dict-view misuse (Py3-valid methods used in Py2-only ways) -------------

def test_dict_keys_indexing_flagged():
    r = analyze_source("first = d.keys()[0]\n")
    assert "dict_view_index_keys" in types(r)


def test_dict_values_indexing_flagged():
    r = analyze_source("v = d.values()[2]\n")
    assert "dict_view_index_values" in types(r)


def test_len_of_dict_keys_flagged():
    r = analyze_source("n = len(d.keys())\n")
    assert "dict_view_len_keys" in types(r)


def test_plain_dict_keys_iteration_not_flagged():
    r = analyze_source("for k in d.keys(): pass\n")
    assert "dict_view_index_keys" not in types(r)
    assert "dict_view_len_keys" not in types(r)


# --- Empty / trivial cases --------------------------------------------------

def test_empty_source():
    r = analyze_source("")
    assert r.findings == []


def test_pure_py3_source_clean():
    src = (
        "from __future__ import print_function, division\n"
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
        "print('ok')\n"
    )
    r = analyze_source(src)
    flagged = {f.construct_type for f in r.findings if f.category != Category.META}
    assert flagged == set(), f"expected no Py2 flags, got {flagged}"
