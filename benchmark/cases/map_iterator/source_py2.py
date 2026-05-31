"""Collection transformation utilities using map() and filter().

In Python 2, map() and filter() return lists. Code here indexes into their
results, takes len() of them, and performs other list operations.

In Python 3, map() and filter() return lazy iterators. The migration must
wrap results in list() wherever list semantics (indexing, len, truthiness
on exhaustion) are relied upon.
"""


def stringify_all(numbers):
    """Convert every number to a string. Returns a list in Py2."""
    return map(str, numbers)


def count_positives(numbers):
    """Count how many values are positive. Py2: len(filter(...)) is valid."""
    return len(filter(lambda x: x > 0, numbers))


def first_even(numbers):
    """Return the first even number. Py2: filter(...)[0] is valid indexing."""
    evens = filter(lambda x: x % 2 == 0, numbers)
    if not evens:
        raise ValueError("no even numbers in sequence")
    return evens[0]


def double_odds(numbers):
    """Double each odd number. Py2: map(f, filter(f, lst)) returns a list."""
    return map(lambda x: x * 2, filter(lambda x: x % 2 != 0, numbers))


def apply_all(funcs, value):
    """Apply each function to value and return the results as a list."""
    return map(lambda f: f(value), funcs)
