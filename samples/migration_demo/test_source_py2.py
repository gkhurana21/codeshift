"""Behavior tests for the migration demo.

Critically, test_average_preserves_int_division pins the Py2 semantics:
sum([1,2,3])/3 == 2, sum([1,2])/2 == 1. A naive migration that leaves `/`
alone will get 2.0 / 1.5 and fail these tests, forcing the repair loop to
swap to `//`. That is the exact "test-feedback drives the migration" demo.
"""

from source_py2 import Adder, average, counts, first_key, has, shout


def test_average_preserves_int_division():
    # Py2: 6/3 = 2 (int division). Py3 `/` gives 2.0, `//` gives 2.
    assert average([1, 2, 3]) == 2
    # Py2: 3/2 = 1. Py3 `/` gives 1.5, `//` gives 1.
    assert average([1, 2]) == 1
    assert isinstance(average([2, 4, 6]), int)


def test_first_key_indexes_dict_view():
    # Py3: dict.keys() returns a view; must wrap in list() for indexing.
    d = {"a": 1, "b": 2}
    assert first_key(d) in d


def test_shout_accepts_str():
    assert shout("hello") == "HELLO"
    assert shout("Python") == "PYTHON"


def test_has_uses_in_operator():
    assert has({"x": 1, "y": 2}, "x") is True
    assert has({"x": 1, "y": 2}, "z") is False


def test_adder_uses_functools_reduce():
    assert Adder(10).add(1, 2, 3) == 16
    assert Adder(0).add() == 0


def test_counts_returns_pairs():
    pairs = counts(["a", "b", "a", "c", "b", "a"])
    as_dict = dict(pairs)
    assert as_dict == {"a": 3, "b": 2, "c": 1}
