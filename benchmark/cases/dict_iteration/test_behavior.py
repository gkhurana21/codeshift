"""Behavioral oracle for dict_iteration.

Py2 semantics:
  - .iteritems()/.itervalues()/.iterkeys() return iterators (migrate to .items()/.values()/.keys()).
  - d.keys() returns a list copy, so modifying d during `for k in d.keys()` is safe;
    the Py3 migration MUST wrap in list() to preserve this snapshot behavior.
"""
from source_py2 import pairs_sorted, inverted, value_sum, remove_keys, merge_sum


def test_pairs_sorted():
    result = pairs_sorted({'c': 3, 'a': 1, 'b': 2})
    assert result == [('a', 1), ('b', 2), ('c', 3)]


def test_pairs_sorted_empty():
    assert pairs_sorted({}) == []


def test_inverted():
    result = inverted({'x': 1, 'y': 2, 'z': 3})
    assert result == {1: 'x', 2: 'y', 3: 'z'}


def test_value_sum():
    assert value_sum({'a': 10, 'b': 20, 'c': 30}) == 60
    assert value_sum({}) == 0


def test_remove_keys_mutation_safe():
    # This triggers RuntimeError in Py3 if d.keys() is NOT wrapped in list().
    d = {'keep_a': 1, 'drop_b': 2, 'keep_c': 3, 'drop_d': 4}
    result = remove_keys(d, lambda k: k.startswith('drop_'))
    assert result == {'keep_a': 1, 'keep_c': 3}


def test_remove_keys_removes_all():
    d = {'x': 1, 'y': 2}
    result = remove_keys(d, lambda k: True)
    assert result == {}


def test_merge_sum():
    base = {'a': 1, 'b': 2}
    result = merge_sum(base, {'b': 10, 'c': 5})
    assert result == {'a': 1, 'b': 12, 'c': 5}
