"""Behavioral oracle for map_iterator.

Py2 semantics: map() and filter() return lists.
Code indexes into results ([0], [-1]), calls len(), checks truthiness, and
chains them. The migration must wrap in list() to preserve these semantics.
"""
import pytest
from source_py2 import stringify_all, count_positives, first_even, double_odds, apply_all


def test_stringify_all_indexable():
    result = stringify_all([1, 2, 3])
    # Py2 returned a list; must be indexable after migration
    assert result[0] == '1'
    assert result[2] == '3'
    assert len(result) == 3


def test_stringify_all_empty():
    result = stringify_all([])
    assert len(result) == 0


def test_count_positives():
    assert count_positives([1, -2, 3, -4, 5]) == 3
    assert count_positives([-1, -2, -3]) == 0
    assert count_positives([]) == 0


def test_first_even():
    assert first_even([1, 3, 4, 5, 6]) == 4
    assert first_even([2]) == 2


def test_first_even_raises_when_none():
    with pytest.raises(ValueError):
        first_even([1, 3, 5])


def test_double_odds_indexable():
    result = double_odds([1, 2, 3, 4, 5])
    # odds: 1, 3, 5 -> doubled: 2, 6, 10
    assert result[0] == 2
    assert list(result) == [2, 6, 10]


def test_apply_all():
    result = apply_all([str, float, int], 3)
    assert result[0] == '3'
    assert result[1] == 3.0
    assert result[2] == 3
