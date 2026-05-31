"""Behavioral oracle for text_encoding.

Py2 semantics: unicode() builtin and basestring abstract type exist.
str.decode() converts bytes to unicode; unicode.encode() converts to bytes.

Migration must:
  - Replace unicode with str  (NameError in Py3 otherwise)
  - Replace basestring with (str, bytes) or str  (NameError otherwise)
  - Ensure to_text() handles both str and bytes inputs
  - Ensure to_bytes() returns bytes
"""
from source_py2 import to_text, to_bytes, is_text, normalize, char_count


def test_to_text_from_bytes():
    assert to_text(b'hello') == 'hello'


def test_to_text_from_bytes_utf8():
    # multi-byte UTF-8 sequence -> unicode
    assert to_text('café'.encode('utf-8')) == 'café'


def test_to_text_passthrough():
    # Already text: should pass through unchanged
    assert to_text('already text') == 'already text'


def test_to_bytes_from_str():
    assert to_bytes('hello') == b'hello'


def test_to_bytes_utf8():
    assert to_bytes('café') == 'café'.encode('utf-8')


def test_to_bytes_passthrough():
    assert to_bytes(b'already bytes') == b'already bytes'


def test_is_text_str():
    assert is_text('hello') is True


def test_is_text_non_string():
    assert is_text(42) is False
    assert is_text(None) is False
    assert is_text([]) is False


def test_normalize_strips_bytes():
    assert normalize(b'  hello  ') == 'hello'


def test_normalize_strips_text():
    assert normalize('  world  ') == 'world'


def test_char_count_ascii():
    assert char_count(b'hello') == 5
    assert char_count('hello') == 5


def test_char_count_multibyte():
    # 'café' is 4 characters but 5 bytes in UTF-8
    assert char_count('café'.encode('utf-8')) == 4
    assert char_count('café') == 4
