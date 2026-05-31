"""Behavioral oracle for report_builder.

Multi-trap: iteritems/itervalues (mechanical) + integer division for shares (F2).
F3 constraint: uses single-entry dicts for category_totals; top_category uses
a dict where the winner is unambiguous by value, not by iteration order.
"""
from source_py2 import category_totals, category_shares, top_category


def test_category_totals_single():
    # Single-element dict: no ordering sensitivity
    assert category_totals({'A': 5}) == {'A': 5}


def test_category_shares_floor():
    # A: 1*100/3 = 33.333 → 33; B: 2*100/3 = 66.666 → 66
    shares = category_shares({'A': 1, 'B': 2})
    assert shares['A'] == 33
    assert shares['B'] == 66


def test_category_shares_one_entry():
    # 5*100/5 = 100 — exact, but that's OK (floor and float agree)
    shares = category_shares({'X': 5})
    assert shares['X'] == 100


def test_category_shares_three():
    # A:1, B:1, C:1 → total=3; each 1*100/3=33
    shares = category_shares({'A': 1, 'B': 1, 'C': 1})
    assert shares['A'] == 33
    assert shares['B'] == 33
    assert shares['C'] == 33


def test_top_category_clear_winner():
    # B has highest count; unambiguous
    assert top_category({'A': 3, 'B': 7, 'C': 1}) == 'B'


def test_top_category_single():
    assert top_category({'only': 99}) == 'only'
