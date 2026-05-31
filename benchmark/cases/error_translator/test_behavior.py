"""Behavioral oracle for error_translator.

F6 oracle: verifies that the re-raise suppresses __context__.
Three-state discriminator:
  1. Unmigrated source (except E, e syntax) → SyntaxError on import → all tests fail.
  2. Naive migration (except E as e; raise AppError) → __context__ is set → asserts fail.
  3. Correct migration (raise AppError(...) from None) → __context__ is None → asserts pass.
  4. Agent drops except entirely → KeyError propagates → pytest.raises(AppError) fails.
"""
import pytest
from source_py2 import AppError, load_config, parse_int, safe_divide


def test_load_config_missing_key():
    with pytest.raises(AppError) as exc_info:
        load_config({}, 'host')
    assert exc_info.value.__context__ is None, (
        "Exception context not suppressed — migrate re-raise as "
        "'raise AppError(...) from None'"
    )


def test_parse_int_invalid():
    with pytest.raises(AppError) as exc_info:
        parse_int('oops')
    assert exc_info.value.__context__ is None, (
        "Exception context not suppressed — add 'from None' to the re-raise"
    )


def test_safe_divide_zero():
    with pytest.raises(AppError) as exc_info:
        safe_divide(1, 0)
    assert exc_info.value.__context__ is None


def test_load_config_hit():
    assert load_config({'host': 'localhost'}, 'host') == 'localhost'


def test_parse_int_valid():
    assert parse_int('42') == 42


def test_safe_divide_normal():
    assert safe_divide(10, 2) == 5
