"""Behavioral oracle for success_rate.

Tests behavior-preservation under a misleading function name: names like
'hit_rate' and 'miss_rate' suggest float output, which may tempt the agent
to use '/' (float division) rather than '//' (floor).  The oracle encodes
Py2-observed floor behavior; a pass requires the agent to preserve it.

Does NOT test F2 undecidability.  The genuinely-intended-float case (where
floor division was the author's bug, not intent) has no single correct oracle
by construction and cannot be scored.
"""
from source_py2 import hit_rate, miss_rate, improvement


def test_hit_rate_floor():
    # 1*100/3 = 33.333... → floor 33
    assert hit_rate(1, 3) == 33
    # 2*100/3 = 66.666... → floor 66
    assert hit_rate(2, 3) == 66
    # 1*100/7 = 14.285... → floor 14
    assert hit_rate(1, 7) == 14


def test_miss_rate_floor():
    # (3-1)*100/3 = 66.666... → floor 66
    assert miss_rate(1, 3) == 66
    # (3-2)*100/3 = 33.333... → floor 33
    assert miss_rate(2, 3) == 33


def test_improvement_floor():
    # (12-10)*100/7 = 200/7 = 28.571... → floor 28
    assert improvement(10, 12, 7) == 28
    # (5-3)*100/9 = 200/9 = 22.222... → floor 22
    assert improvement(3, 5, 9) == 22
