"""Functional combinators using itertools."""
import itertools


def zip_with(fn, seq_a, seq_b):
    return list(itertools.imap(fn, seq_a, seq_b))


def zip_pairs(seq_a, seq_b):
    return list(itertools.izip(seq_a, seq_b))


def zip_longest_pad(seq_a, seq_b, fill=None):
    return list(itertools.izip_longest(seq_a, seq_b, fillvalue=fill))


def product_pairs(seq_a, seq_b):
    return list(itertools.imap(
        lambda ab: ab[0] * ab[1],
        itertools.izip(seq_a, seq_b)
    ))
