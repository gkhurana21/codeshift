"""Comparison and ordering utilities."""


def compare(a, b):
    return cmp(a, b)


def sort_reversed(items):
    return sorted(items, cmp=lambda a, b: -cmp(a, b))


def clamp_cmp(value, lo, hi):
    if cmp(value, lo) < 0:
        return lo
    if cmp(value, hi) > 0:
        return hi
    return value


def sign(value):
    return cmp(value, 0)
