"""Exception handling utilities using Py2 exception binding syntax.

Python 2 allows:  except ExcType, variable:
Python 3 requires: except ExcType as variable:

The comma syntax is a parse error in Py3. This module exercises both the
single-type and multi-type forms of the old syntax.
"""


def safe_int(s):
    """Parse s as an integer; return None on failure."""
    try:
        return int(s)
    except (ValueError, TypeError), e:
        return None


def safe_divide(a, b):
    """Return float(a) / float(b); raise ValueError on zero divisor."""
    try:
        return float(a) / float(b)
    except ZeroDivisionError, e:
        raise ValueError("cannot divide by zero: " + str(e))


def try_each(converters, value):
    """Try converters in order; return the first success, or raise the last error."""
    last_exc = None
    for conv in converters:
        try:
            return conv(value)
        except Exception, e:
            last_exc = e
    raise last_exc


def get_nested(obj, *keys):
    """Navigate nested dicts/lists by key sequence; return None on missing key."""
    try:
        for k in keys:
            obj = obj[k]
        return obj
    except (KeyError, IndexError, TypeError), e:
        return None
