"""Integer arithmetic utilities.

In Python 2, the / operator between two integers performs floor division.
These functions rely on that Py2 semantics; the migrated Py3 version must
preserve floor-division behavior by using //.
"""


def average(numbers):
    """Return the arithmetic mean using Py2 integer division (floor)."""
    if not numbers:
        raise ValueError("average of empty sequence")
    return sum(numbers) / len(numbers)


def median(numbers):
    """Return the median using integer index arithmetic.

    Py2: len(s) / 2 is a floor-division index; (a + b) / 2 is floor-divided.
    """
    if not numbers:
        raise ValueError("median of empty sequence")
    s = sorted(numbers)
    mid = len(s) / 2
    if len(s) % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2
    return s[mid]


def percentage(part, whole):
    """Integer percentage: part * 100 / whole, floor-divided in Py2."""
    if whole == 0:
        raise ZeroDivisionError("whole must be non-zero")
    return part * 100 / whole


def distribute(total, buckets):
    """Split total into buckets of equal integer size (floor division)."""
    if buckets <= 0:
        raise ValueError("buckets must be positive")
    per_bucket = total / buckets
    remainder = total - per_bucket * buckets
    return [per_bucket] * buckets, remainder
