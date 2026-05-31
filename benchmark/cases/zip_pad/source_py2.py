"""Sequence alignment utilities."""


def align(seq_a, seq_b):
    return list(map(None, seq_a, seq_b))


def align3(seq_a, seq_b, seq_c):
    return list(map(None, seq_a, seq_b, seq_c))


def merge_columns(cols):
    if not cols:
        return []
    if len(cols) == 1:
        return [(item,) for item in cols[0]]
    result = list(map(None, cols[0], cols[1]))
    for extra in cols[2:]:
        result = list(map(None, result, extra))
    return result
