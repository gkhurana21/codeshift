"""Behavioral oracle for bandwidth_estimator.

Tests behavior-preservation under misleading function names: 'bytes_per_second'
and 'bits_per_ms' suggest float results, which may tempt the agent to use '/'
rather than '//'.  The oracle encodes Py2-observed floor behavior.

Does NOT test F2 undecidability.  The genuinely-intended-float case has no
single correct oracle by construction and cannot be scored.
"""
from source_py2 import bytes_per_second, bits_per_ms, eta_seconds


def test_bytes_per_second_floor():
    # 100*1000/300 = 333.333... → floor 333
    assert bytes_per_second(100, 300) == 333
    # 1*1000/7 = 142.857... → floor 142
    assert bytes_per_second(1, 7) == 142


def test_bits_per_ms_floor():
    # 10*8/3 = 26.666... → floor 26
    assert bits_per_ms(10, 3) == 26
    # 5*8/6 = 6.666... → floor 6
    assert bits_per_ms(5, 6) == 6


def test_eta_seconds_floor():
    # 100/7 = 14.285... → floor 14
    assert eta_seconds(100, 7) == 14
    # 50/3 = 16.666... → floor 16
    assert eta_seconds(50, 3) == 16
