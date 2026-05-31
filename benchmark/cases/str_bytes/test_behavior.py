"""Behavioral oracle for str_bytes.

Py2 semantics: str is bytes; ord(c) converts a single-byte char to int.
In Py3, bytes iteration yields int directly; the migration must drop the
ord() calls and use bytes-native operations. All oracles pass bytes literals.
"""
import pytest
from source_py2 import xor_bytes, bytes_to_hex, hex_to_bytes, byte_sum


def test_xor_self_is_zero():
    data = b'\x01\x02\x03'
    result = xor_bytes(data, data)
    assert result == b'\x00\x00\x00'


def test_xor_known_values():
    # 0xff ^ 0x0f = 0xf0
    result = xor_bytes(b'\xff\x0f', b'\x0f\xff')
    assert result == b'\xf0\xf0'


def test_xor_length_mismatch():
    with pytest.raises(ValueError):
        xor_bytes(b'\x01\x02', b'\x03')


def test_bytes_to_hex_known():
    assert bytes_to_hex(b'\xde\xad') == 'dead'
    assert bytes_to_hex(b'\x00\xff') == '00ff'
    assert bytes_to_hex(b'') == ''


def test_hex_roundtrip():
    original = b'\xde\xad\xbe\xef'
    assert hex_to_bytes(bytes_to_hex(original)) == original


def test_hex_to_bytes_known():
    assert hex_to_bytes('deadbeef') == b'\xde\xad\xbe\xef'
    assert hex_to_bytes('') == b''


def test_byte_sum():
    assert byte_sum(b'\x01\x02\x03') == 6
    assert byte_sum(b'\xff') == 255
    assert byte_sum(b'') == 0
