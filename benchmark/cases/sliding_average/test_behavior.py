"""Behavioral oracle for sliding_average.

Tests behavior-preservation under misleading names: 'running_mean' and
'windowed_mean' suggest continuous (float) output.  The oracle encodes
Py2-observed floor behavior; a pass requires the agent to preserve it.

Does NOT test F2 undecidability.  The genuinely-intended-float case has no
single correct oracle by construction and cannot be scored.
"""
from source_py2 import running_mean, windowed_mean, quantize


def test_running_mean_floor():
    # (1+2+4)/3 = 7/3 = 2.333... → floor 2
    assert running_mean([1, 2, 4]) == 2
    # (3+4)/2 = 7/2 = 3.5 → floor 3
    assert running_mean([3, 4]) == 3
    # (1+2+3+4+5)/5 = 15/5 = 3 — exact; use different
    # (2+3+4)/3 = 9/3 = 3 — exact; use (1+3+4)/3 = 8/3 = 2
    assert running_mean([1, 3, 4]) == 2


def test_windowed_mean_floor():
    # last 2 of [2,3,4]: sum=7, 7/2 = 3.5 → floor 3
    assert windowed_mean([2, 3, 4], 2) == 3
    # last 2 of [1,2,3,4,5]: sum=9, 9/2 = 4.5 → floor 4
    assert windowed_mean([1, 2, 3, 4, 5], 2) == 4


def test_quantize_floor():
    # 10/3 = 3, 3*3 = 9
    assert quantize(10, 3) == 9
    # 7/4 = 1, 1*4 = 4
    assert quantize(7, 4) == 4
    # 11/5 = 2, 2*5 = 10
    assert quantize(11, 5) == 10
