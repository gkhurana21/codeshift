"""Behavioral oracle for reduce_builtin."""
from source_py2 import product, flatten_one, running_max


def test_product_multiple():
    assert product([2, 3, 4]) == 24


def test_product_single():
    assert product([7]) == 7


def test_flatten_one_level():
    assert flatten_one([[1, 2], [3], [4, 5]]) == [1, 2, 3, 4, 5]


def test_flatten_empty_sublists():
    assert flatten_one([[], [1], []]) == [1]


def test_flatten_empty_outer():
    assert flatten_one([]) == []


def test_running_max():
    assert running_max([3, 1, 4, 1, 5, 9, 2]) == 9


def test_running_max_single():
    assert running_max([42]) == 42
