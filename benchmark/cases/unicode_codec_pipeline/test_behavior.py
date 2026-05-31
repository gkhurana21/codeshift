"""Behavioral oracle for unicode_codec_pipeline."""
from source_py2 import to_utf8, from_utf8, b64_encode, b64_decode


def test_to_utf8_ascii():
    assert to_utf8('hello') == b'hello'


def test_to_utf8_non_ascii():
    assert to_utf8('caf\xe9') == b'caf\xc3\xa9'


def test_to_utf8_already_bytes():
    assert to_utf8(b'hello') == b'hello'


def test_from_utf8_bytes():
    assert from_utf8(b'caf\xc3\xa9') == 'caf\xe9'


def test_from_utf8_already_str():
    assert from_utf8('hello') == 'hello'


def test_b64_encode_ascii():
    assert b64_encode('hello') == 'aGVsbG8='


def test_b64_roundtrip_ascii():
    assert b64_decode(b64_encode('hello')) == 'hello'


def test_b64_roundtrip_non_ascii():
    assert b64_decode(b64_encode('caf\xe9')) == 'caf\xe9'
