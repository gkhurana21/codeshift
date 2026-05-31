"""Behavioral oracle for exception_syntax.

Py2 semantics: the comma-form `except E, e:` binds the exception to `e`.
Migrated Py3 code must use `except E as e:`. Behavior is otherwise identical.
"""
import pytest
from source_py2 import safe_int, safe_divide, try_each, get_nested


def test_safe_int_valid():
    assert safe_int("42") == 42
    assert safe_int("-7") == -7
    assert safe_int("0") == 0


def test_safe_int_invalid():
    assert safe_int("abc") is None
    assert safe_int("") is None
    assert safe_int(None) is None


def test_safe_divide_exact():
    assert safe_divide(10, 4) == 2.5
    assert safe_divide(6, 2) == 3.0


def test_safe_divide_zero_raises():
    with pytest.raises(ValueError, match="cannot divide by zero"):
        safe_divide(1, 0)


def test_try_each_first_success():
    # int("3.14") fails, float("3.14") succeeds
    result = try_each([int, float, str], "3.14")
    assert result == 3.14


def test_try_each_last_resort():
    # int and float both fail on "hello"; str always succeeds
    result = try_each([int, float, str], "hello")
    assert result == "hello"


def test_get_nested_hit():
    obj = {'a': {'b': {'c': 42}}}
    assert get_nested(obj, 'a', 'b', 'c') == 42


def test_get_nested_miss():
    obj = {'a': {'b': 1}}
    assert get_nested(obj, 'a', 'x') is None
    assert get_nested(obj, 'z') is None


def test_get_nested_list():
    obj = [10, [20, 30]]
    assert get_nested(obj, 1, 0) == 20
    assert get_nested(obj, 5) is None
