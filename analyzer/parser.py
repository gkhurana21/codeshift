"""Thin parso wrapper that returns a Py2 parse tree + tolerated errors.

parso is error-tolerant: it returns a partial tree even when syntax errors
exist. That's what we want, because Py2 files we receive can have constructs
parso's grammar27 still rejects (notably `<>`). Those gaps are covered by a
token-level fallback in `detectors`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import parso
from parso.python.tree import Module

from config import PY2_GRAMMAR_VERSION


@dataclass
class ParseResult:
    tree: Module
    errors: List["ParseErrorInfo"]


@dataclass
class ParseErrorInfo:
    line: int
    column: int
    message: str


_GRAMMAR = None


def _grammar():
    global _GRAMMAR
    if _GRAMMAR is None:
        _GRAMMAR = parso.load_grammar(version=PY2_GRAMMAR_VERSION)
    return _GRAMMAR


def parse_py2(source: str) -> ParseResult:
    """Parse a Python 2 source string. Always returns a tree (possibly with errors)."""
    g = _grammar()
    tree = g.parse(source)
    errors: List[ParseErrorInfo] = []
    for err in g.iter_errors(tree):
        line, col = err.start_pos
        errors.append(ParseErrorInfo(line=line, column=col, message=err.message))
    return ParseResult(tree=tree, errors=errors)
