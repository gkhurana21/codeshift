"""Aggregation utilities using reduce."""


def product(numbers):
    return reduce(lambda x, y: x * y, numbers)


def flatten_one(nested):
    return reduce(lambda acc, xs: acc + xs, nested, [])


def running_max(items):
    return reduce(lambda a, b: a if a > b else b, items)
