"""Defensive parsing of LLM output into valid Python 3 source.

Models occasionally ignore "no fences, no commentary" instructions. This module
strips:
  * triple-backtick fences (with or without a `python` language tag),
  * a single leading prose line like "Here is the migrated code:",
  * trailing prose after the last code-like line.

Then it verifies the result with `ast.parse`. On failure, the caller does one
corrective retry (see agent/tools.py::transform_code).
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Optional


_FENCE_OPEN = re.compile(r"^\s*```(?:python|py|python3)?\s*\n", re.IGNORECASE)
_FENCE_CLOSE = re.compile(r"\n```\s*$")


@dataclass
class ParsedCode:
    code: str
    parse_error: Optional[str]

    @property
    def ok(self) -> bool:
        return self.parse_error is None


def strip_fences_and_prose(raw: str) -> str:
    """Best-effort: remove markdown fences and obvious surrounding prose."""
    s = raw.strip()
    if not s:
        return s

    # 1. If the whole thing is wrapped in ```...``` (or ```python...```), peel it.
    if s.startswith("```"):
        # Strip leading fence (with optional language tag).
        m = _FENCE_OPEN.match(s)
        if m:
            s = s[m.end():]
        else:
            # Fence without a newline before content - rare but happens.
            s = re.sub(r"^```(?:python|py|python3)?\s*", "", s, count=1, flags=re.IGNORECASE)
        # Strip trailing fence.
        m = _FENCE_CLOSE.search(s)
        if m:
            s = s[: m.start()]
        else:
            s = re.sub(r"```\s*$", "", s)

    # 2. Otherwise, look for the FIRST fenced code block inside prose
    #    (model output sometimes is: "Here you go:\n```python\n<code>\n```\nLet me know!")
    elif "```" in s:
        # Find a fenced block; if found, use its contents.
        m = re.search(r"```(?:python|py|python3)?\s*\n(.*?)\n```", s, flags=re.IGNORECASE | re.DOTALL)
        if m:
            s = m.group(1)

    # 3. Strip a single leading prose line like "Here is the migrated code:".
    #    Only do this if the first line is plainly prose (no `=`, no Python tokens).
    lines = s.split("\n", 1)
    if len(lines) == 2 and _looks_like_prose_intro(lines[0]):
        s = lines[1]

    return s.rstrip() + "\n"


_PROSE_INTRO_RE = re.compile(
    r"^\s*(here(?:'s| is)|the (?:migrated|converted|updated) (?:code|version)|"
    r"below is|i('?ve)? (?:converted|migrated))",
    re.IGNORECASE,
)


def _looks_like_prose_intro(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    if line.endswith(":") and not line.strip().startswith(("def ", "class ", "if ", "for ", "while ", "try", "else", "elif ", "with ", "@")):
        return _PROSE_INTRO_RE.match(line) is not None or len(line) < 80
    return False


def parse_or_error(source: str) -> ParsedCode:
    """Try ast.parse(source). Return ParsedCode with a parse_error if invalid."""
    try:
        ast.parse(source)
        return ParsedCode(code=source, parse_error=None)
    except SyntaxError as e:
        msg = f"{e.__class__.__name__}: {e.msg} at line {e.lineno}, col {e.offset}"
        return ParsedCode(code=source, parse_error=msg)


def parse_model_output(raw: str) -> ParsedCode:
    """Full pipeline: strip wrapping, then verify with ast.parse."""
    stripped = strip_fences_and_prose(raw)
    return parse_or_error(stripped)
