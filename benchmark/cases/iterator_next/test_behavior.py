"""Behavioral oracle for iterator_next."""
from source_py2 import first_match, peek, skip_until


def test_first_match_found():
    assert first_match([1, 3, 4, 6], lambda x: x % 2 == 0) == 4


def test_first_match_none():
    assert first_match([1, 3, 5], lambda x: x % 2 == 0) is None


def test_first_match_empty():
    assert first_match([], lambda x: True) is None


def test_peek():
    it = iter([10, 20, 30])
    assert peek(it) == 10
    assert peek(it) == 20


def test_skip_until():
    it = iter([1, 2, 3, 4, 5])
    assert skip_until(it, lambda x: x > 3) == 4
