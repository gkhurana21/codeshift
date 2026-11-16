"""Behavioral oracle for validation_chain.

F6 oracle: re-raised errors must print on their own, as in Python 2.
  1. Unmigrated (except E, e syntax) → SyntaxError on import → all tests fail.
  2. Naive migration (except E as e; raise ...) → prints the caught error too → fails.
  3. `raise ... from e` → prints the cause too → fails.
  4. Correct: `raise ... from None`, or raising after the except block → passes.
  5. Agent drops except → ValidationError propagates instead of ParseError → fails.

Fixed 2026-11-16: the original assertion was `__context__ is None`, which
`from None` can't satisfy (it sets __suppress_context__ and leaves __context__).
"""
import traceback

import pytest
from source_py2 import ValidationError, ParseError, validate_age, parse_record


def _prints_chained_error(exc):
    """True if printing `exc` would also print another exception.

    Python 2 never chained exceptions. Python 3 also prints the exception that
    was being handled ("During handling of the above exception...") unless the
    re-raise uses `from None` or happens after the except block, and prints the
    cause for `from e`. Checking the printed output tests exactly that, rather
    than `__context__`, which `from None` leaves set.
    """
    text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return (
        "During handling of the above exception" in text
        or "The above exception was the direct cause" in text
    )


def test_validate_age_valid():
    assert validate_age('25') == 25


def test_validate_age_bad_int_clean_error():
    with pytest.raises(ValidationError) as exc_info:
        validate_age('abc')
    assert not _prints_chained_error(exc_info.value), "Re-raise also prints the caught exception, which Python 2 never did"


def test_validate_age_out_of_range():
    with pytest.raises(ValidationError):
        validate_age('200')


def test_parse_record_valid():
    result = parse_record('Alice|30|alice@example.com')
    assert result == {'name': 'Alice', 'age': 30, 'email': 'alice@example.com'}


def test_parse_record_bad_age_clean_error():
    with pytest.raises(ParseError) as exc_info:
        parse_record('Alice|bad|alice@example.com')
    assert not _prints_chained_error(exc_info.value), "Re-raise also prints the caught exception, which Python 2 never did"


def test_parse_record_wrong_field_count():
    with pytest.raises(ParseError):
        parse_record('only_one_field')
