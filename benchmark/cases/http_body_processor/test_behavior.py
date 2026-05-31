"""Behavioral oracle for http_body_processor."""
import pytest
from source_py2 import parse_content_length, strip_chunked_body, body_to_lines


def test_parse_content_length_present():
    headers = b'HTTP/1.1 200 OK\r\nContent-Length: 42\r\nContent-Type: text/plain'
    assert parse_content_length(headers) == 42


def test_parse_content_length_case_insensitive():
    headers = b'content-length: 7\r\nHost: example.com'
    assert parse_content_length(headers) == 7


def test_parse_content_length_missing():
    headers = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain'
    assert parse_content_length(headers) == 0


def test_strip_chunked_body():
    # "3\r\nabc\r\n3\r\ndef\r\n0\r\n" -> b'abcdef'
    chunk = b'3\r\nabc\r\n3\r\ndef\r\n0\r\n'
    assert strip_chunked_body(chunk) == b'abcdef'


def test_strip_chunked_body_single():
    chunk = b'5\r\nhello\r\n0\r\n'
    assert strip_chunked_body(chunk) == b'hello'


def test_body_to_lines():
    body = b'alpha\nbeta\n\ngamma\n'
    assert body_to_lines(body) == [b'alpha', b'beta', b'gamma']


def test_body_to_lines_empty():
    assert body_to_lines(b'\n\n\n') == []
