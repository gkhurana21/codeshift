"""Dictionary utilities that index and slice .keys() / .values().

In Python 2, dict.keys() and dict.values() return plain lists.
This code indexes and slices them directly; the Py3 migration must wrap
these calls in list() where indexing or slicing is performed.
"""


def first_key(d):
    """Return the first key (Py2: d.keys() is a list)."""
    if not d:
        raise KeyError("dict is empty")
    return d.keys()[0]


def last_value(d):
    """Return the last value (Py2: d.values()[-1] is valid)."""
    if not d:
        raise KeyError("dict is empty")
    return d.values()[-1]


def key_slice(d, start, stop):
    """Return a slice of the key list (Py2: d.keys() supports slicing)."""
    return d.keys()[start:stop]


def nth_item(d, n):
    """Return the nth (key, value) pair as a tuple."""
    keys = d.keys()
    if n >= len(keys):
        raise IndexError("index out of range")
    k = keys[n]
    return k, d[k]


def common_keys(d1, d2):
    """Return sorted list of keys present in both dicts."""
    return sorted(list(set(d1.keys()) & set(d2.keys())))
