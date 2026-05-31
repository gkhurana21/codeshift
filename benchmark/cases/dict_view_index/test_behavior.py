"""Behavioral oracle for dict_view_index.

Py2 semantics: dict.keys() and dict.values() return lists, which are
indexable and sliceable. Py3 returns views; migration must wrap in list()
wherever indexing or slicing occurs.
"""
import pytest
from source_py2 import first_key, last_value, key_slice, nth_item


def test_first_key_single_element():
    # Single-element dict: only one possible answer
    assert first_key({'z': 99}) == 'z'


def test_last_value_single_element():
    assert last_value({'m': 42}) == 42


def test_key_slice_within_bounds():
    # Single-element: [0:1] must return ['a']
    assert key_slice({'a': 1}, 0, 1) == ['a']


def test_key_slice_beyond_bounds():
    # Slicing past the end returns empty list (list semantics, not error)
    assert key_slice({'a': 1}, 5, 10) == []


def test_nth_item_first():
    # Single-element dict: n=0 must return that one pair
    assert nth_item({'x': 7}, 0) == ('x', 7)


def test_nth_item_out_of_range():
    with pytest.raises(IndexError):
        nth_item({'a': 1}, 5)


def test_first_key_raises_on_empty():
    with pytest.raises(KeyError):
        first_key({})
