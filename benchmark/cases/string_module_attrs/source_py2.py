"""Character classification utilities."""
import string


def is_alphabetic(s):
    return all(c in string.letters for c in s)


def is_lowercase_word(s):
    return bool(s) and all(c in string.lowercase for c in s)


def count_digits(s):
    return sum(1 for c in s if c in string.digits)


def strip_non_alpha(s):
    return ''.join(c for c in s if c in string.letters)
