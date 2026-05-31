"""Unicode and encoding utilities.

In Python 2, there are two distinct string types:
  - str:     raw bytes (default string literal type)
  - unicode: decoded text (u"..." literals)

The builtins unicode() and basestring are Py2-only.
str.decode() and unicode.encode() bridge between the two types.

In Python 3:
  - str is unicode (text)
  - bytes is the raw-bytes type
  - unicode() and basestring do not exist; use str() and (str, bytes) instead.
  - bytes objects have .decode(); str objects do NOT have .decode().
"""


def to_text(s, encoding='utf-8'):
    """Coerce s to unicode (Py2) / str (Py3). Decodes bytes; passes text through."""
    if isinstance(s, unicode):
        return s
    return s.decode(encoding)


def to_bytes(s, encoding='utf-8'):
    """Coerce s to str/bytes. Encodes unicode; passes str through."""
    if isinstance(s, unicode):
        return s.encode(encoding)
    return s


def is_text(s):
    """Return True if s is any string type (str or unicode in Py2)."""
    return isinstance(s, basestring)


def normalize(s, encoding='utf-8'):
    """Decode s to text (if needed), strip whitespace, return as text."""
    return to_text(s, encoding).strip()


def char_count(s, encoding='utf-8'):
    """Return the number of unicode characters (not bytes) in s."""
    return len(to_text(s, encoding))
