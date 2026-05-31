"""Type-checking utilities for string values."""


def is_string(value):
    return isinstance(value, basestring)


def require_string(value, name='value'):
    if not isinstance(value, basestring):
        raise TypeError(name + ' must be a string')


def stringify_if_needed(value):
    if isinstance(value, basestring):
        return value
    return str(value)


def all_strings(items):
    return all(isinstance(item, basestring) for item in items)
