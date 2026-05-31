"""Behavioral oracle for xrange_iteration."""
from source_py2 import first_n, sum_range, chunked


def test_first_n():
    assert first_n(5) == [0, 1, 2, 3, 4]


def test_first_n_zero():
    assert first_n(0) == []


def test_sum_range_step():
    # 1+3+5+7+9 = 25
    assert sum_range(1, 10, 2) == 25


def test_sum_range_default_step():
    assert sum_range(1, 5) == 10


def test_chunked_even():
    assert chunked([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_chunked_remainder():
    assert chunked([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_chunked_larger_than_list():
    assert chunked([1, 2], 5) == [[1, 2]]
