"""Top-level analyzer entrypoints: `analyze_source` and `analyze_file`."""

from __future__ import annotations

import logging
from pathlib import Path

from analyzer.detectors import run_all
from analyzer.parser import parse_py2
from analyzer.schema import ParseIssue, Report

log = logging.getLogger("codeshift.analyzer")


def analyze_source(source: str, path: str = "<string>") -> Report:
    """Analyze a Python 2 source string and return a `Report`."""
    parsed = parse_py2(source)
    findings, future_flags = run_all(parsed.tree, source)
    report = Report(
        path=path,
        parse_errors=[
            ParseIssue(line=e.line, column=e.column, message=e.message)
            for e in parsed.errors
        ],
        future_flags=future_flags,
        findings=findings,
    )
    log.info(
        "analyzed path=%s findings=%d semantic=%d parse_errors=%d",
        path,
        len(report.findings),
        sum(1 for f in report.findings if f.semantic_risk),
        len(report.parse_errors),
    )
    return report


def analyze_file(path: str | Path) -> Report:
    p = Path(path)
    source = p.read_text(encoding="utf-8", errors="replace")
    return analyze_source(source, path=str(p))
