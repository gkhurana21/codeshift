"""Behavioral oracle for config_value_encoder."""
import pytest
from source_py2 import get_value, merge_defaults, encode_pair


def test_get_value_present():
    assert get_value(b'timeout=60\nmode=slow\n', 'timeout') == b'60'


def test_get_value_second_key():
    assert get_value(b'timeout=60\nmode=slow\n', 'mode') == b'slow'


def test_get_value_missing():
    assert get_value(b'retries=5\n', 'timeout') is None


def test_get_value_empty_config():
    assert get_value(b'', 'timeout') is None


def test_merge_defaults_override():
    result = merge_defaults(b'timeout=99\n')
    assert result['timeout'] == b'99'


def test_merge_defaults_fallback():
    result = merge_defaults(b'timeout=99\n')
    assert result['retries'] == '3'
    assert result['mode'] == 'fast'


def test_get_value_with_spaces():
    assert get_value(b'  key  =  val  \n', 'key') == b'val'
