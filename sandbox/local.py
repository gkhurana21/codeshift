"""Local subprocess sandbox - runs pytest in the host venv.

NOT a security boundary. Phase 3 replaces this with a hardened Docker runner.
Used in Phase 2 so the agent's run_tests tool can actually exercise tests.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List

from sandbox.base import TestResult

log = logging.getLogger("codeshift.sandbox.local")


_STDOUT_MAX = 8_000  # chars; keeps prompts tractable


class LocalSubprocessSandbox:
    """Runs pytest in a subprocess with a JUnit-XML report for structured parsing."""

    def __init__(self, python: str | None = None):
        # Default to the current interpreter (the venv's python).
        self.python = python or sys.executable

    def run_pytest(self, work_dir: Path, test_path: Path, timeout_s: int = 60) -> TestResult:
        work_dir = Path(work_dir).resolve()
        test_path = Path(test_path)
        if not test_path.is_absolute():
            test_path = (work_dir / test_path).resolve()
        if not work_dir.exists():
            raise FileNotFoundError(f"work_dir does not exist: {work_dir}")
        if not test_path.exists():
            raise FileNotFoundError(f"test file does not exist: {test_path}")

        # Critical: kill any stale bytecode caches between iterations.
        # Python's .pyc invalidation uses second-resolution mtime; if two
        # consecutive iterations write the source within the same second,
        # pytest can import the stale .pyc and report the OLD behavior.
        _purge_pycache(work_dir)

        with tempfile.TemporaryDirectory() as tmp:
            junit = Path(tmp) / "junit.xml"
            cmd = [
                self.python,
                "-B",                        # don't write .pyc files
                "-m",
                "pytest",
                str(test_path),
                "-v",
                "--tb=short",
                "--no-header",
                "-p",
                "no:cacheprovider",
                f"--junitxml={junit}",
                "--rootdir",
                str(work_dir),
            ]
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            log.info("sandbox cmd: %s", " ".join(cmd))
            start = time.monotonic()
            timed_out = False
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(work_dir),
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                    env=env,
                )
                stdout = proc.stdout or ""
                stderr = proc.stderr or ""
            except subprocess.TimeoutExpired as e:
                timed_out = True
                stdout = (e.stdout or b"").decode("utf-8", errors="replace") if isinstance(e.stdout, (bytes, bytearray)) else (e.stdout or "")
                stderr = (e.stderr or b"").decode("utf-8", errors="replace") if isinstance(e.stderr, (bytes, bytearray)) else (e.stderr or "")
                stdout += f"\n[sandbox] killed after timeout={timeout_s}s\n"
            duration = time.monotonic() - start

            combined = (stdout + ("\n[stderr]\n" + stderr if stderr.strip() else "")).strip()
            if len(combined) > _STDOUT_MAX:
                combined = combined[:_STDOUT_MAX] + "\n... [stdout truncated]"

            passed, failed, errors, collected, tbs = _parse_junit(junit, fallback_stdout=combined)
            result = TestResult(
                passed=passed,
                failed=failed,
                errors=errors,
                collected=collected,
                tracebacks=tbs,
                stdout=combined,
                duration_s=round(duration, 3),
                timed_out=timed_out,
            )
            log.info(
                "sandbox result passed=%d failed=%d errors=%d collected=%d timed_out=%s duration=%.2fs",
                result.passed, result.failed, result.errors, result.collected, result.timed_out, result.duration_s,
            )
            return result


def _purge_pycache(root: Path) -> None:
    """Recursively delete __pycache__ directories under `root`."""
    for cache in root.rglob("__pycache__"):
        try:
            shutil.rmtree(cache)
        except OSError as e:
            log.warning("could not remove %s: %s", cache, e)


def _parse_junit(junit_path: Path, fallback_stdout: str) -> tuple[int, int, int, int, List[str]]:
    """Parse the JUnit XML pytest emits.

    Returns (passed, failed, errors, collected, tracebacks).
    Falls back to (0, 0, 1, 0, [stdout]) when the XML is missing/empty
    (e.g. pytest exited before writing anything - collection-level failure).
    """
    if not junit_path.exists() or junit_path.stat().st_size == 0:
        # Collection error / pytest crashed - surface the stdout.
        return 0, 0, 1, 0, [fallback_stdout or "pytest produced no output"]

    try:
        tree = ET.parse(junit_path)
    except ET.ParseError:
        return 0, 0, 1, 0, [f"junit XML unparseable\n{fallback_stdout}"]

    root = tree.getroot()
    # pytest emits <testsuites> with one <testsuite> child.
    suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
    total_failures = 0
    total_errors = 0
    total_tests = 0
    total_skipped = 0
    tracebacks: List[str] = []
    for suite in suites:
        total_failures += int(suite.get("failures", "0") or "0")
        total_errors += int(suite.get("errors", "0") or "0")
        total_tests += int(suite.get("tests", "0") or "0")
        total_skipped += int(suite.get("skipped", "0") or "0")
        for case in suite.findall("testcase"):
            for tag in ("failure", "error"):
                el = case.find(tag)
                if el is not None:
                    name = f"{case.get('classname', '')}::{case.get('name', '')}".lstrip(":")
                    msg = (el.get("message") or "").strip()
                    body = (el.text or "").strip()
                    tracebacks.append(f"[{tag.upper()}] {name}\n{msg}\n{body}".strip())

    passed = max(0, total_tests - total_failures - total_errors - total_skipped)
    # If the run collected nothing AND we have no failures/errors, the XML is
    # technically valid but the test file was empty - flag as a 1-error case so
    # the agent doesn't think it succeeded silently.
    if total_tests == 0 and total_failures == 0 and total_errors == 0:
        return 0, 0, 1, 0, [
            "pytest collected 0 tests - check that the test file contains test_*/Test* items.\n"
            + (fallback_stdout or "")
        ]

    return passed, total_failures, total_errors, total_tests, tracebacks
