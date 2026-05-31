"""CLI: `python -m analyzer.scan path/to/file.py`.

Prints a human-readable report to stdout and writes the JSON report to
`<file>.findings.json` (or to the path given by --out).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from analyzer.analyzer import analyze_file
from analyzer.schema import Category, Report
from config import DEFAULT_OUTPUT_DIR, configure_logging


# ANSI - only used when stdout is a TTY.
_USE_COLOR = sys.stdout.isatty()


def _c(s: str, code: str) -> str:
    if not _USE_COLOR:
        return s
    return f"\x1b[{code}m{s}\x1b[0m"


_SEV_COLOR = {"error": "31", "warning": "33", "info": "36"}
_CAT_COLOR = {"syntax": "35", "semantic": "31;1", "stdlib": "34", "meta": "37"}


def render_report(report: Report) -> str:
    lines: list[str] = []
    lines.append(_c(f"== CodeShift analyzer ==", "1"))
    lines.append(f"file: {report.path}")
    if report.future_flags:
        lines.append(f"__future__: {', '.join(report.future_flags)}")
    if report.parse_errors:
        lines.append(_c(f"parse errors: {len(report.parse_errors)} (analyzer continued)", "33"))
        for pe in report.parse_errors[:5]:
            lines.append(f"  L{pe.line}:{pe.column}  {pe.message}")
        if len(report.parse_errors) > 5:
            lines.append(f"  ...and {len(report.parse_errors) - 5} more")
    lines.append("")
    summary = report.summary()
    lines.append(
        f"findings: {summary['total']}  "
        f"({_c('semantic_risk=' + str(summary['semantic_risk']), '31;1')})  "
        f"by_category={summary['by_category']}"
    )
    lines.append("")
    if not report.findings:
        lines.append(_c("no Py2 constructs detected.", "32"))
        return "\n".join(lines)

    header = f"{'LINE':>5}  {'COL':>3}  {'SEV':<7}  {'CATEGORY':<8}  {'TYPE':<28}  RISK  SNIPPET"
    lines.append(_c(header, "1"))
    lines.append("-" * len(header))
    for f in report.findings:
        cat = _c(f.category.value, _CAT_COLOR.get(f.category.value, "0"))
        sev = _c(f.severity.value, _SEV_COLOR.get(f.severity.value, "0"))
        risk = _c("YES", "31;1") if f.semantic_risk else " . "
        snippet = f.snippet.replace("\n", "\\n")
        if len(snippet) > 60:
            snippet = snippet[:57] + "..."
        lines.append(
            f"{f.line:>5}  {f.column:>3}  {sev:<7}  {cat:<8}  {f.construct_type:<28}  {risk}   {snippet}"
        )
        if f.notes:
            lines.append(f"       note: {f.notes}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(prog="analyzer.scan", description="Analyze a Python 2 source file.")
    parser.add_argument("path", help="Path to a .py file to analyze.")
    parser.add_argument(
        "--out",
        default=None,
        help="Where to write the JSON report. Default: <PROJECT_ROOT>/out/<basename>.findings.json",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress human-readable output.")
    args = parser.parse_args(argv)

    src_path = Path(args.path)
    if not src_path.exists():
        print(f"error: {src_path} does not exist", file=sys.stderr)
        return 2

    report = analyze_file(src_path)

    if not args.quiet:
        print(render_report(report))

    out_path = (
        Path(args.out)
        if args.out
        else DEFAULT_OUTPUT_DIR / f"{src_path.stem}.findings.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report.model_dump_json(indent=2))
    if not args.quiet:
        print(f"\nwrote JSON report -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
