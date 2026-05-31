"""Range-based iteration utilities."""


def first_n(n):
    return list(xrange(n))


def sum_range(start, stop, step=1):
    total = 0
    for i in xrange(start, stop, step):
        total += i
    return total


def chunked(items, size):
    result = []
    for start in xrange(0, len(items), size):
        result.append(items[start:start + size])
    return result
