"""Large integer handling utilities."""

MAX_ID = 9999999999999999999L


def is_large_int(value):
    return isinstance(value, (int, long))


def to_long(value):
    return long(value)


def safe_id(value):
    if isinstance(value, (int, long)):
        return value
    raise TypeError('expected integer, got ' + type(value).__name__)
