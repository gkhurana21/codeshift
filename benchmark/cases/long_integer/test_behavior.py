"""Behavioral oracle for long_integer."""
import pytest
from source_py2 import MAX_ID, is_large_int, to_long, safe_id


def test_max_id_is_int():
    assert isinstance(MAX_ID, int)


def test_max_id_value():
    assert MAX_ID == 9999999999999999999


def test_is_large_int_true():
    assert is_large_int(42) is True
    assert is_large_int(10 ** 30) is True


def test_is_large_int_false():
    assert is_large_int('x') is False
    assert is_large_int(3.14) is False


def test_to_long_string():
    assert to_long('42') == 42


def test_to_long_float():
    assert to_long(3.7) == 3


def test_safe_id_int():
    assert safe_id(42) == 42


def test_safe_id_invalid():
    with pytest.raises(TypeError):
        safe_id('not-an-int')
