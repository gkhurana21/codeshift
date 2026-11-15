"""Bite-check: every oracle must fail on its own unmigrated Py2 source.

An oracle that passes on code nobody migrated isn't testing the trap, so a
green oracle here is a broken case. Each case runs in its own temp directory,
the same way the benchmark runner does it, because every case names its oracle
test_behavior.py and pytest can't collect forty files with one name together.

Needs no API keys and makes no LLM calls, so it runs in CI.

Usage:
    python -m benchmark.bite_check                     # all cases
    python -m benchmark.bite_check --cases zip_pad,str_bytes

Exit code 0 when every case bites, 1 when any case passes on unmigrated source.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from benchmark.runner import CASES_DIR, discover_cases

# pytest exit codes: 1 = tests failed, 2 = collection error (e.g. the Py2
# source raises SyntaxError on import). Both mean the oracle bit. 0 means it
# passed on unmigrated code; anything else means the oracle itself is broken.
_BIT = {1, 2}
# Collection errors print the real exception on an "E   SyntaxError: ..." line.
# Test failures under --tb=line print "path.py:17: TypeError: ..." or
# "path.py:17: assert ...".
_E_LINE_RE = re.compile(r"^E\s+([A-Z]\w*(?:Error|Exception))\b")
_TB_LINE_RE = re.compile(r"\.py:\d+: ([A-Z]\w*(?:Error|Exception))\b")
_TB_ASSERT_RE = re.compile(r"\.py:\d+: assert ")


@dataclass
class BiteResult:
    name: str
    bit: bool
    exit_code: int
    passed: int
    not_passed: int
    first_error: str


def _first_error(output: str) -> str:
    lines = output.splitlines()
    for line in lines:
        m = _E_LINE_RE.match(line)
        if m:
            return m.group(1)
    for line in lines:
        m = _TB_LINE_RE.search(line)
        if m:
            return m.group(1)
        if _TB_ASSERT_RE.search(line):
            return "AssertionError"
    return "-"


def check_case(case_dir: Path, timeout_s: int = 60) -> BiteResult:
    with tempfile.TemporaryDirectory(prefix=f"bite_{case_dir.name}_") as tmp:
        work = Path(tmp)
        shutil.copy2(case_dir / "source_py2.py", work / "source_py2.py")
        shutil.copy2(case_dir / "test_behavior.py", work / "test_behavior.py")
        junit = work / "junit.xml"
        proc = subprocess.run(
            [
                sys.executable, "-B", "-m", "pytest", "test_behavior.py",
                "-q", "--tb=line", "-p", "no:cacheprovider",
                f"--junitxml={junit}", "--rootdir", str(work),
            ],
            cwd=work, capture_output=True, text=True, timeout=timeout_s,
        )
        tests = failures = errors = skipped = 0
        if junit.exists():
            suite = ET.parse(junit).getroot()
            suite = suite if suite.tag == "testsuite" else suite.find("testsuite")
            tests = int(suite.get("tests", 0))
            failures = int(suite.get("failures", 0))
            errors = int(suite.get("errors", 0))
            skipped = int(suite.get("skipped", 0))
        not_passed = failures + errors
        passed = max(tests - not_passed - skipped, 0)
        return BiteResult(
            name=case_dir.name,
            bit=proc.returncode in _BIT,
            exit_code=proc.returncode,
            passed=passed,
            not_passed=not_passed,
            first_error=_first_error(proc.stdout + proc.stderr),
        )


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="benchmark.bite_check", description=__doc__.splitlines()[0])
    p.add_argument("--cases", default=None, help="Comma-separated subset of case names (default: all).")
    args = p.parse_args(argv)

    case_dirs = discover_cases(CASES_DIR)
    if args.cases:
        wanted = {c.strip() for c in args.cases.split(",") if c.strip()}
        unknown = wanted - {d.name for d in case_dirs}
        if unknown:
            print(f"unknown case(s): {', '.join(sorted(unknown))}", file=sys.stderr)
            return 2
        case_dirs = [d for d in case_dirs if d.name in wanted]

    results = [check_case(d) for d in case_dirs]
    width = max(len(r.name) for r in results)
    print(f" {'CASE':<{width}}  BITES  FAILING  PASSING  FIRST ERROR")
    for r in results:
        mark = "yes" if r.bit else "NO"
        print(f" {r.name:<{width}}  {mark:<5}  {r.not_passed:>7}  {r.passed:>7}  {r.first_error}")

    broken = [r for r in results if not r.bit]
    print(f"\n {len(results) - len(broken)}/{len(results)} oracles fail on unmigrated source.")
    if broken:
        for r in broken:
            print(f" BROKEN: {r.name} (pytest exit {r.exit_code}) does not fail on unmigrated source.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
