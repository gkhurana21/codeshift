"""Behavioral oracle for validation_chain.

F6 oracle: verifies that re-raises suppress __context__.
Three-state discriminator:
  1. Unmigrated (except E, e syntax) → SyntaxError on import → all tests fail.
  2. Naive migration (except E as e; raise ...) → __context__ set → asserts fail.
  3. Correct migration (raise ... from None) → __context__ is None → pass.
  4. Agent drops except → ValidationError propagates instead of ParseError → fails.
"""
import pytest
from source_py2 import ValidationError, ParseError, validate_age, parse_record


def test_validate_age_valid():
    assert validate_age('25') == 25


def test_validate_age_bad_int_clean_error():
    with pytest.raises(ValidationError) as exc_info:
        validate_age('abc')
    assert exc_info.value.__context__ is None, (
        "Exception context not suppressed — add 'from None' to the re-raise"
    )


def test_validate_age_out_of_range():
    with pytest.raises(ValidationError):
        validate_age('200')


def test_parse_record_valid():
    result = parse_record('Alice|30|alice@example.com')
    assert result == {'name': 'Alice', 'age': 30, 'email': 'alice@example.com'}


def test_parse_record_bad_age_clean_error():
    with pytest.raises(ParseError) as exc_info:
        parse_record('Alice|bad|alice@example.com')
    assert exc_info.value.__context__ is None


def test_parse_record_wrong_field_count():
    with pytest.raises(ParseError):
        parse_record('only_one_field')
