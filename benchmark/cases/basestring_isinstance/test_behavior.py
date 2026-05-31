"""Behavioral oracle for basestring_isinstance."""
import pytest
from source_py2 import is_string, require_string, stringify_if_needed, all_strings


def test_is_string_str():
    assert is_string('hello') is True


def test_is_string_empty():
    assert is_string('') is True


def test_is_string_int():
    assert is_string(42) is False


def test_require_string_raises():
    with pytest.raises(TypeError):
        require_string(42)


def test_require_string_passes():
    require_string('ok')  # no exception


def test_stringify_already_str():
    assert stringify_if_needed('x') == 'x'


def test_stringify_int():
    assert stringify_if_needed(99) == '99'


def test_all_strings_true():
    assert all_strings(['a', 'b', 'c']) is True


def test_all_strings_false():
    assert all_strings(['a', 1]) is False


def test_all_strings_mixed_types():
    assert all_strings([1, 2, 3]) is False
