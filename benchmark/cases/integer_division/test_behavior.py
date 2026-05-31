"""Behavioral oracle for integer_division.

Py2 semantics: integer / integer = floor(a / b).
Every assertion here encodes the Py2-correct result; the migrated Py3 code
must produce these values to pass.
"""
import pytest
from source_py2 import average, median, percentage, distribute


def test_average_floor():
    # (1+2)/2 = 3/2 = 1 in Py2 (floor), not 1.5
    assert average([1, 2]) == 1
    # (3+4)/2 = 7/2 = 3 in Py2
    assert average([3, 4]) == 3
    # (1+4)/2 = 5/2 = 2 in Py2, not 2.5
    assert average([1, 4]) == 2
    # (1+2+4)/3 = 7/3 = 2 in Py2, not 2.333...
    assert average([1, 2, 4]) == 2


def test_median_odd():
    # 3-element: mid = 3/2 = 1 (floor); s[1] = 2
    assert median([1, 2, 3]) == 2
    # 5-element: mid = 5/2 = 2; s[2] = 30
    assert median([10, 20, 30, 40, 50]) == 30


def test_median_even():
    # 4-element: mid = 4/2 = 2; (s[1]+s[2])/2 = (2+3)/2 = 5/2 = 2 (floor)
    assert median([1, 2, 3, 4]) == 2
    # 2-element: mid = 1; (s[0]+s[1])/2 = (1+2)/2 = 1 (floor)
    assert median([1, 2]) == 1


def test_percentage_floor():
    # 1 * 100 / 3 = 100/3 = 33 (floor)
    assert percentage(1, 3) == 33
    # 2 * 100 / 3 = 200/3 = 66 (floor)
    assert percentage(2, 3) == 66
    # 1 * 100 / 7 = 100/7 = 14 in Py2, not 14.285...
    assert percentage(1, 7) == 14


def test_distribute_floor():
    # 10 / 3 = 3 per bucket, remainder = 10 - 3*3 = 1
    buckets, remainder = distribute(10, 3)
    assert buckets == [3, 3, 3]
    assert remainder == 1
    # 7 / 2 = 3 per bucket in Py2 (floor), not 3.5; remainder = 7 - 3*2 = 1
    buckets, remainder = distribute(7, 2)
    assert buckets == [3, 3]
    assert remainder == 1


def test_average_raises_on_empty():
    with pytest.raises(ValueError):
        average([])
