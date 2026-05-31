# Hand-written Py2 demo file for the Phase 2 agent.
# Combines multiple semantic-risk constructs the test suite will pin down.

def average(numbers):
    """Mean of a list of integers - Py2 returns an integer (floor)."""
    return sum(numbers) / len(numbers)


def first_key(d):
    """Return the first key from a dict - Py2 dict.keys() is a list, Py3 is a view."""
    return d.keys()[0]


def shout(s):
    """Uppercase a string. Py2 must accept both str and unicode."""
    if isinstance(s, basestring):
        return unicode(s).upper()
    raise TypeError("expected string")


def has(d, k):
    """Membership check - Py2 idiom."""
    return d.has_key(k)


class Adder:
    """Sum *args plus a base, using the Py2 reduce() builtin."""

    def __init__(self, base):
        self.base = base

    def add(self, *args):
        return reduce(lambda a, b: a + b, args, self.base)


def counts(words):
    """Count word occurrences. Uses iteritems for iteration."""
    out = {}
    for w in words:
        out[w] = out.get(w, 0) + 1
    pairs = []
    for k, v in out.iteritems():
        pairs.append((k, v))
    return pairs
