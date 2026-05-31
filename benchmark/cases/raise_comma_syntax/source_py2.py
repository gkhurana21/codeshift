"""Validation utilities with explicit exception raising."""


def require_positive(n, name='value'):
    if n <= 0:
        raise ValueError, name + ' must be positive, got ' + str(n)


def require_type(value, expected_type, name='value'):
    if not isinstance(value, expected_type):
        raise TypeError, name + ' must be ' + expected_type.__name__


def parse_json_key(d, key):
    if key not in d:
        raise KeyError, 'missing required key: ' + key
    return d[key]
