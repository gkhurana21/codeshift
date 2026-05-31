"""Behavioral oracle for has_key_method."""
from source_py2 import safe_get, contains_all, merge_missing


def test_safe_get_present():
    assert safe_get({'a': 1}, 'a') == 1


def test_safe_get_missing_returns_none():
    assert safe_get({'a': 1}, 'b') is None


def test_safe_get_explicit_default():
    assert safe_get({}, 'x', 42) == 42


def test_contains_all_true():
    assert contains_all({'a': 1, 'b': 2}, ['a', 'b']) is True


def test_contains_all_false():
    assert contains_all({'a': 1}, ['a', 'b']) is False


def test_contains_all_single_true():
    assert contains_all({'x': 1}, ['x']) is True


def test_merge_missing_fills_gaps():
    assert merge_missing({'a': 1}, {'a': 9, 'b': 2}) == {'a': 1, 'b': 2}


def test_merge_missing_no_overlap():
    assert merge_missing({'a': 1}, {'b': 2}) == {'a': 1, 'b': 2}
