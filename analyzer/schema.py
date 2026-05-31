"""Pydantic schema for analyzer findings.

Pinning the JSON shape here keeps the analyzer and the Phase 2 agent in sync.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Category(str, Enum):
    """High-level grouping for a finding."""

    SYNTAX = "syntax"           # mechanical syntax-only rewrites
    SEMANTIC = "semantic"       # behavior may change
    STDLIB = "stdlib"           # stdlib reorganization
    META = "meta"               # informational (e.g. __future__ imports)


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Finding(BaseModel):
    """A single Py2 construct detected in source."""

    line: int = Field(..., ge=1, description="1-based line number.")
    column: int = Field(..., ge=0, description="0-based column.")
    construct_type: str = Field(..., description="Stable identifier, e.g. 'print_statement'.")
    category: Category
    severity: Severity
    snippet: str = Field(..., description="Source snippet (best-effort).")
    semantic_risk: bool = Field(
        ...,
        description="True if migrating this can change runtime behavior, not just syntax.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Free-form context (e.g. 'operand types unknown - heuristic flag').",
    )


class ParseIssue(BaseModel):
    """A parse-level error parso reported (we still try to walk the rest)."""

    line: int
    column: int
    message: str


class Report(BaseModel):
    """Per-file analysis report."""

    path: str
    parse_errors: List[ParseIssue] = Field(default_factory=list)
    future_flags: List[str] = Field(
        default_factory=list,
        description="Names imported from __future__ (e.g. 'division', 'print_function').",
    )
    findings: List[Finding] = Field(default_factory=list)

    def summary(self) -> dict:
        """Counts for quick console rendering."""
        by_cat: dict[str, int] = {}
        semantic = 0
        for f in self.findings:
            by_cat[f.category.value] = by_cat.get(f.category.value, 0) + 1
            if f.semantic_risk:
                semantic += 1
        return {
            "total": len(self.findings),
            "semantic_risk": semantic,
            "by_category": by_cat,
            "parse_errors": len(self.parse_errors),
            "future_flags": list(self.future_flags),
        }
