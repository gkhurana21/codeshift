"""Behavioral oracle for unicode_template_renderer."""
from source_py2 import render, slugify, truncate


def test_render_basic():
    assert render('{name} says hello', {'name': 'World'}) == 'World says hello'


def test_render_non_string_value():
    assert render('count: {n}', {'n': 42}) == 'count: 42'


def test_render_multiple_keys():
    assert render('{a} and {b}', {'a': 'foo', 'b': 'bar'}) == 'foo and bar'


def test_slugify_simple():
    assert slugify('Hello World!') == 'hello-world'


def test_slugify_numbers():
    assert slugify('abc 123 def') == 'abc-123-def'


def test_slugify_non_string_input():
    assert slugify(42) == '42'


def test_truncate_long():
    assert truncate('abcdefghij', 7) == 'abcd...'


def test_truncate_exact():
    assert truncate('abcde', 5) == 'abcde'


def test_truncate_short():
    assert truncate('abc', 10) == 'abc'
