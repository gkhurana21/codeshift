"""Spreadsheet-style column operations."""


def zip_columns(col_a, col_b):
    return map(None, col_a, col_b)


def transpose_with_padding(rows):
    if not rows:
        return []
    return list(map(None, *rows))


def diff_columns(before, after):
    paired = map(None, before, after)
    return [(b, a) for b, a in paired if b != a]
