"""Behavioral oracle for zip_exhaustion."""
from source_py2 import stats, find_and_count, multi_pass


def test_stats_count_matches_length():
    lst, count = stats(['a', 'b', 'c'], [1, 2, 3])
    assert lst == [('a', 1), ('b', 2), ('c', 3)]
    assert count == 3


def test_stats_single():
    lst, count = stats(['x'], [99])
    assert lst == [('x', 99)]
    assert count == 1


def test_find_and_count():
    val, remaining = find_and_count(['x', 'y', 'z'], [1, 2, 3], 'y')
    assert val == 2
    assert remaining == 2  # x and z remain after y consumed


def test_find_and_count_missing_key():
    # In Py2, zip() returns a list; after the for-loop, list(pairs) yields all pairs again.
    # Correctly-migrated Py3 wraps zip() in list() so remaining reflects the full pairing.
    val, remaining = find_and_count(['a', 'b'], [1, 2], 'missing')
    assert val is None
    assert remaining == 2  # Py2 (list zip): full 2-pair list; Py3 migrated: same


def test_multi_pass():
    first, second = multi_pass([2, 3, 4], [10, 20, 30])
    assert first == [12, 23, 34]
    assert second == [20, 60, 120]
