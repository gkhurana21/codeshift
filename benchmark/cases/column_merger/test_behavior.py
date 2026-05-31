"""Behavioral oracle for column_merger."""
from source_py2 import zip_columns, transpose_with_padding, diff_columns


def test_zip_columns_equal():
    assert list(zip_columns([1, 2], [10, 20])) == [(1, 10), (2, 20)]


def test_zip_columns_pad():
    assert list(zip_columns([1, 2, 3], [10, 20])) == [(1, 10), (2, 20), (3, None)]


def test_zip_columns_empty_first():
    assert list(zip_columns([], [1, 2])) == [(None, 1), (None, 2)]


def test_transpose_jagged():
    result = transpose_with_padding([[1, 2], [3], [4, 5, 6]])
    assert result == [(1, 3, 4), (2, None, 5), (None, None, 6)]


def test_transpose_single_col():
    assert transpose_with_padding([[1, 2, 3]]) == [(1,), (2,), (3,)]


def test_diff_columns_changes_only():
    assert diff_columns([1, 2, 3], [1, 9, 3]) == [(2, 9)]


def test_diff_columns_with_padding():
    # before shorter: padded None pairs where before[i] != after[i]
    result = diff_columns([1, 2], [1, 2, 3])
    assert (None, 3) in result
