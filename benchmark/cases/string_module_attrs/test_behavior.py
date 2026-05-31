"""Behavioral oracle for string_module_attrs."""
from source_py2 import is_alphabetic, is_lowercase_word, count_digits, strip_non_alpha


def test_is_alphabetic_true():
    assert is_alphabetic('hello') is True


def test_is_alphabetic_with_digit():
    assert is_alphabetic('hello1') is False


def test_is_lowercase_word_true():
    assert is_lowercase_word('abc') is True


def test_is_lowercase_word_uppercase():
    assert is_lowercase_word('ABC') is False


def test_strip_non_alpha():
    assert strip_non_alpha('h3ll0 w0rld') == 'hll wrld'


def test_strip_non_alpha_clean():
    assert strip_non_alpha('hello') == 'hello'
