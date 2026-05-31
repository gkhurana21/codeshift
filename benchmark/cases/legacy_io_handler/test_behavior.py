"""Behavioral oracle for legacy_io_handler.

Multi-trap: iteritems (mechanical) + unicode/basestring type checks (F1-family).
"""
from source_py2 import format_config, normalize_value


def test_format_config_sorted():
    # sorted output, no ordering sensitivity
    result = format_config({'b': 'two', 'a': 'one'})
    assert result == 'a=one\nb=two'


def test_format_config_single():
    assert format_config({'x': 'y'}) == 'x=y'


def test_normalize_value_str():
    assert normalize_value('  hello  ') == 'hello'


def test_normalize_value_non_str():
    assert normalize_value(42) == 42


def test_normalize_value_no_strip_needed():
    assert normalize_value('clean') == 'clean'
