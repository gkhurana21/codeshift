"""Behavioral oracle for zip_pad."""
from source_py2 import align, align3, merge_columns


def test_align_equal_length():
    assert align([1, 2, 3], [4, 5, 6]) == [(1, 4), (2, 5), (3, 6)]


def test_align_pad_right():
    assert align([1, 2, 3], [4]) == [(1, 4), (2, None), (3, None)]


def test_align_pad_left():
    assert align([1], [4, 5, 6]) == [(1, 4), (None, 5), (None, 6)]


def test_align_empty_left():
    assert align([], [1, 2]) == [(None, 1), (None, 2)]


def test_align3_pad():
    result = align3([1, 2], [3], [4, 5, 6])
    assert result == [(1, 3, 4), (2, None, 5), (None, None, 6)]


def test_align3_equal():
    assert align3([1], [2], [3]) == [(1, 2, 3)]
