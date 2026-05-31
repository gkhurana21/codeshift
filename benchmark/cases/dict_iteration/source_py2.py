"""Dictionary iteration and mutation utilities.

Two distinct Py2 dict behaviors demonstrated here:

1. dict.iteritems() / itervalues() / iterkeys(): Py2-only iterator methods.
   Migration: replace with .items() / .values() / .keys().

2. dict.keys() returns a LIST COPY in Py2, so mutating the dict while
   iterating d.keys() is safe. In Py3, d.keys() returns a VIEW; mutating
   the dict during iteration raises RuntimeError.
   Migration: wrap in list() — `for k in list(d.keys()):`.
"""


def pairs_sorted(d):
    """Return list of (key, value) pairs sorted by key."""
    return sorted(d.iteritems())


def inverted(d):
    """Return a new dict with keys and values swapped."""
    return {v: k for k, v in d.iteritems()}


def value_sum(d):
    """Sum all values in the dict."""
    total = 0
    for v in d.itervalues():
        total += v
    return total


def remove_keys(d, predicate):
    """Remove all entries whose key satisfies predicate (mutate in place).

    Py2: d.keys() returns a list snapshot; deleting during iteration is safe.
    Py3: d.keys() returns a view; migration must snapshot with list(d.keys()).
    """
    for k in d.keys():
        if predicate(k):
            del d[k]
    return d


def merge_sum(base, updates):
    """Add values from updates into base, creating keys that don't exist."""
    for k, v in updates.iteritems():
        base[k] = base.get(k, 0) + v
    return base
