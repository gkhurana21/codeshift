"""Behavioral oracle for error_translator.

F6 oracle: the re-raised AppError must print on its own, as in Python 2.
  1. Unmigrated source (except E, e syntax) → SyntaxError on import → all tests fail.
  2. Naive migration (except E as e; raise AppError) → prints the caught error too → fails.
  3. `raise AppError(...) from e` → prints the cause too → fails.
  4. Correct: `raise AppError(...) from None`, or raising after the except block → passes.
  5. Agent drops except entirely → KeyError propagates → pytest.raises(AppError) fails.

Fixed 2026-11-16: the original assertion was `__context__ is None`, which
`from None` can't satisfy (it sets __suppress_context__ and leaves __context__).
"""
import traceback

import pytest
from source_py2 import AppError, load_config, parse_int, safe_divide


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


def test_load_config_missing_key():
    with pytest.raises(AppError) as exc_info:
        load_config({}, 'host')
    assert not _prints_chained_error(exc_info.value), "Re-raise also prints the caught exception, which Python 2 never did"


def test_parse_int_invalid():
    with pytest.raises(AppError) as exc_info:
        parse_int('oops')
    assert not _prints_chained_error(exc_info.value), "Re-raise also prints the caught exception, which Python 2 never did"


def test_safe_divide_zero():
    with pytest.raises(AppError) as exc_info:
        safe_divide(1, 0)
    assert not _prints_chained_error(exc_info.value), "Re-raise also prints the caught exception, which Python 2 never did"


def test_load_config_hit():
    assert load_config({'host': 'localhost'}, 'host') == 'localhost'


def test_parse_int_valid():
    assert parse_int('42') == 42


def test_safe_divide_normal():
    assert safe_divide(10, 2) == 5
