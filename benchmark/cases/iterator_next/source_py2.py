"""Iterator utilities."""


def first_match(iterable, predicate):
    it = iter(iterable)
    while True:
        try:
            item = it.next()
        except StopIteration:
            return None
        if predicate(item):
            return item


def peek(iterator):
    return iterator.next()


def skip_until(iterator, predicate):
    while True:
        val = iterator.next()
        if predicate(val):
            return val
