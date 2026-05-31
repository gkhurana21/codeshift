"""Codec pipeline for text serialization and transport encoding."""
from __future__ import unicode_literals
import base64


def to_utf8(text):
    if isinstance(text, unicode):
        return text.encode('utf-8')
    return text


def from_utf8(data):
    if isinstance(data, unicode):
        return data
    return data.decode('utf-8')


def b64_encode(text):
    raw = to_utf8(text)
    return base64.b64encode(raw).decode('ascii')


def b64_decode(encoded):
    raw = base64.b64decode(encoded.encode('ascii'))
    return from_utf8(raw)
