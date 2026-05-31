"""Behavioral oracle for apply_builtin."""
from source_py2 import call_with_args, call_with_kwargs, invoke_all


def test_call_with_args():
    assert call_with_args(lambda a, b: a + b, [3, 4]) == 7


def test_call_with_args_single():
    assert call_with_args(lambda x: x * 2, [5]) == 10


def test_call_with_kwargs():
    def f(a, b=1):
        return a + b
    assert call_with_kwargs(f, [10], {'b': 5}) == 15


def test_call_with_kwargs_default():
    def f(a, b=1):
        return a + b
    assert call_with_kwargs(f, [10], {}) == 11


def test_invoke_all():
    assert invoke_all(lambda x, y: x * y, [[2, 3], [4, 5]]) == [6, 20]


def test_invoke_all_single():
    assert invoke_all(lambda x, y: x - y, [[10, 3]]) == [7]
