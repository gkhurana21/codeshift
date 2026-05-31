"""Behavioral oracle for cmp_builtin."""
from source_py2 import compare, sort_reversed, clamp_cmp, sign


def test_compare_less_than():
    assert compare(1, 2) < 0


def test_compare_equal():
    assert compare(3, 3) == 0


def test_compare_greater_than():
    assert compare(5, 2) > 0


def test_sort_reversed():
    assert sort_reversed([3, 1, 4, 1, 5]) == [5, 4, 3, 1, 1]


def test_sort_reversed_already_sorted():
    assert sort_reversed([1, 2, 3]) == [3, 2, 1]


def test_clamp_below():
    assert clamp_cmp(-5, 0, 10) == 0


def test_clamp_above():
    assert clamp_cmp(15, 0, 10) == 10


def test_clamp_within():
    assert clamp_cmp(5, 0, 10) == 5


def test_sign_negative():
    assert sign(-3) < 0


def test_sign_zero():
    assert sign(0) == 0


def test_sign_positive():
    assert sign(7) > 0
