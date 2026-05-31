"""Behavioral oracle for itertools_izip_imap."""
from source_py2 import zip_with, zip_pairs, zip_longest_pad, product_pairs


def test_zip_with():
    assert zip_with(lambda a, b: a + b, [1, 2, 3], [10, 20, 30]) == [11, 22, 33]


def test_zip_pairs():
    assert zip_pairs([1, 2], ['a', 'b']) == [(1, 'a'), (2, 'b')]


def test_zip_pairs_truncates():
    assert zip_pairs([1, 2, 3], ['a', 'b']) == [(1, 'a'), (2, 'b')]


def test_zip_longest_pad():
    result = zip_longest_pad([1, 2, 3], [10], fill=0)
    assert result == [(1, 10), (2, 0), (3, 0)]


def test_zip_longest_no_pad_needed():
    assert zip_longest_pad([1, 2], [3, 4]) == [(1, 3), (2, 4)]


def test_product_pairs():
    assert product_pairs([2, 3, 4], [3, 2, 1]) == [6, 6, 4]
