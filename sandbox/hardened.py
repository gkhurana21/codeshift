"""Hardened subprocess sandbox for Phase 3 benchmark runs.

Hardens the local subprocess runner with three explicit protections:

  1. PROCESS-GROUP KILL on timeout: the subprocess is launched as a new
     session (start_new_session=True), so on timeout we send SIGKILL to the
     entire process group, not just the top-level pytest process. This
     prevents lingering worker processes from surviving a hung test.

  2. MEMORY CAP via resource.RLIMIT_AS: applied inside the child via
     preexec_fn before exec. Caps virtual address space to prevent a runaway
     test from exhausting host RAM. Default: 2 GiB (generous enough for
     pytest + a test module; reduce if needed for tighter environments).
     On macOS, RLIMIT_AS limits virtual address space; on Linux it limits
     virtual memory. The cap is non-fatal on apply-failure (logged + ignored).

  3. All Phase 2 .pyc-staleness guards carried forward: python -B flag,
     PYTHONDONTWRITEBYTECODE=1 in env, and an explicit __pycache__ purge
     before each run.

TRUST MODEL: this sandbox runs trusted, project-authored benchmark code.
It is NOT a security boundary for arbitrary / untrusted user input.
Do not use it to execute code from external sources without review.
"""

from __future__ import annotations

import logging
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

from sandbox.base import TestResult

log = logging.getLogger("codeshift.sandbox.hardened")

_STDOUT_MAX = 8_000          # chars; keeps prompts tractable
_DEFAULT_MEMORY_BYTES = 2 * 1024 ** 3   # 2 GiB virtual address space cap


def _apply_memory_limit(limit_bytes: int) -> None:
    """Called as preexec_fn in the child process: apply RLIMIT_AS.

    Non-fatal: if setrlimit fails (e.g. the soft limit is already below what
    we'd set, or the OS rejects it), we log to stderr and continue. A failed
    rlimit is better than crashing the subprocess before pytest even starts.
    """
    try:
        resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
    except (ValueError, OSError) as exc:
        print(f"[sandbox] RLIMIT_AS not applied ({exc}); continuing without memory cap",
              file=sys.stderr)


class HardenedSubprocessSandbox:
    """Subprocess sandbox with process-group kill, memory cap, and .pyc guards.

    Drop-in replacement for LocalSubprocessSandbox; satisfies the same
    SandboxRunner protocol. Preferred for Phase 3 benchmark runs.
    """

    def __init__(
        self,
        python: Optional[str] = None,
        memory_limit_bytes: int = _DEFAULT_MEMORY_BYTES,
    ):
        self.python = python or sys.executable
        self.memory_limit_bytes = memory_limit_bytes

    def run_pytest(self, work_dir: Path, test_path: Path, timeout_s: int = 60) -> TestResult:
        work_dir = Path(work_dir).resolve()
        test_path = Path(test_path)
        if not test_path.is_absolute():
            test_path = (work_dir / test_path).resolve()
        if not work_dir.exists():
            raise FileNotFoundError(f"work_dir does not exist: {work_dir}")
        if not test_path.exists():
            raise FileNotFoundError(f"test file does not exist: {test_path}")

        # Carry forward the Phase 2 .pyc-staleness fix.
        _purge_pycache(work_dir)

        with tempfile.TemporaryDirectory() as tmp:
            junit = Path(tmp) / "junit.xml"
            cmd = [
                self.python,
                "-B",
                "-m", "pytest",
                str(test_path),
                "-v", "--tb=short", "--no-header",
                "-p", "no:cacheprovider",
                f"--junitxml={junit}",
                "--rootdir", str(work_dir),
            ]
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            mem_limit = self.memory_limit_bytes

            def _preexec() -> None:
                # start_new_session already called setsid(); we only set rlimit here.
                _apply_memory_limit(mem_limit)

            log.info(
                "hardened sandbox cmd timeout=%ds mem_cap=%dMiB: %s",
                timeout_s, mem_limit // (1024 ** 2), " ".join(cmd),
            )
            start = time.monotonic()
            timed_out = False
            stdout = stderr = ""

            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(work_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    start_new_session=True,   # new session -> new process group
                    preexec_fn=_preexec,      # set RLIMIT_AS in child before exec
                )
                try:
                    raw_out, raw_err = proc.communicate(timeout=timeout_s)
                    stdout = raw_out.decode("utf-8", errors="replace")
                    stderr = raw_err.decode("utf-8", errors="replace")
                except subprocess.TimeoutExpired:
                    timed_out = True
                    # Kill every process in the group (pytest workers included).
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        proc.kill()  # fallback: kill the process directly
                    raw_out, raw_err = proc.communicate()
                    stdout = raw_out.decode("utf-8", errors="replace") if raw_out else ""
                    stderr = raw_err.decode("utf-8", errors="replace") if raw_err else ""
                    stdout += f"\n[sandbox] process group killed after timeout={timeout_s}s\n"

            except Exception as exc:
                log.error("hardened sandbox failed to launch subprocess: %s", exc)
                return TestResult(
                    passed=0, failed=0, errors=1, collected=0,
                    tracebacks=[f"Sandbox launch error: {exc}"],
                    timed_out=False,
                )

            duration = time.monotonic() - start
            combined = (stdout + ("\n[stderr]\n" + stderr if stderr.strip() else "")).strip()
            if len(combined) > _STDOUT_MAX:
                combined = combined[:_STDOUT_MAX] + "\n... [stdout truncated]"

            passed, failed, errors, collected, tbs = _parse_junit(junit, fallback_stdout=combined)
            result = TestResult(
                passed=passed, failed=failed, errors=errors, collected=collected,
                tracebacks=tbs, stdout=combined,
                duration_s=round(duration, 3),
                timed_out=timed_out,
            )
            log.info(
                "hardened sandbox result passed=%d failed=%d errors=%d "
                "collected=%d timed_out=%s duration=%.2fs",
                result.passed, result.failed, result.errors,
                result.collected, result.timed_out, result.duration_s,
            )
            return result


# ---------------------------------------------------------------------------
# Private utilities
# ---------------------------------------------------------------------------

def _purge_pycache(root: Path) -> None:
    """Recursively delete __pycache__ directories under `root`."""
    for cache in root.rglob("__pycache__"):
        try:
            shutil.rmtree(cache)
        except OSError as exc:
            log.warning("could not remove %s: %s", cache, exc)


def _parse_junit(
    junit_path: Path, fallback_stdout: str
) -> tuple[int, int, int, int, List[str]]:
    """Parse JUnit XML produced by pytest.

    Returns (passed, failed, errors, collected, tracebacks).
    Falls back to (0, 0, 1, 0, [stdout]) when the XML is missing/malformed.
    """
    if not junit_path.exists() or junit_path.stat().st_size == 0:
        return 0, 0, 1, 0, [fallback_stdout or "pytest produced no output"]

    try:
        tree = ET.parse(junit_path)
    except ET.ParseError:
        return 0, 0, 1, 0, [f"junit XML unparseable\n{fallback_stdout}"]

    root = tree.getroot()
    suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
    total_failures = total_errors = total_tests = total_skipped = 0
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
    if total_tests == 0 and total_failures == 0 and total_errors == 0:
        return 0, 0, 1, 0, [
            "pytest collected 0 tests - check the test file has test_*/Test* items.\n"
            + (fallback_stdout or "")
        ]

    return passed, total_failures, total_errors, total_tests, tracebacks
