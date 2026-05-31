"""Behavioral oracle for raise_comma_syntax."""
import pytest
from source_py2 import require_positive, require_type, parse_json_key


def test_require_positive_raises():
    with pytest.raises(ValueError):
        require_positive(-1, 'count')


def test_require_positive_zero_raises():
    with pytest.raises(ValueError):
        require_positive(0)


def test_require_positive_passes():
    require_positive(5)  # no exception


def test_require_type_raises():
    with pytest.raises(TypeError):
        require_type('hello', int, 'n')


def test_require_type_passes():
    require_type(42, int)  # no exception


def test_parse_json_key_missing():
    with pytest.raises(KeyError):
        parse_json_key({}, 'x')


def test_parse_json_key_found():
    assert parse_json_key({'k': 'v'}, 'k') == 'v'
