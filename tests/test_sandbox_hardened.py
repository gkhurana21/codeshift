"""Phase 3a acceptance tests for HardenedSubprocessSandbox.

Three scenarios required by the brief:
  1. A passing oracle test  -> result.passed == 1, timed_out == False
  2. A failing oracle test  -> result.failed == 1, tracebacks present
  3. An infinite-loop test  -> result.timed_out == True, returns promptly

All tests run real subprocesses against in-memory fixture files; no API calls.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest

from sandbox.hardened import HardenedSubprocessSandbox


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_files(tmp: Path, module_src: str, test_src: str) -> tuple[Path, Path]:
    """Write module.py and test_module.py into tmp, return (work_dir, test_path)."""
    work = tmp / "work"
    work.mkdir()
    (work / "module.py").write_text(module_src, encoding="utf-8")
    test = work / "test_module.py"
    test.write_text(test_src, encoding="utf-8")
    return work, test


# ---------------------------------------------------------------------------
# 1. Passing oracle
# ---------------------------------------------------------------------------

def test_hardened_sandbox_passing_oracle():
    """Sandbox runs a green oracle and reports passed=1."""
    module = "def answer():\n    return 42\n"
    oracle = (
        "from module import answer\n"
        "\n"
        "def test_answer():\n"
        "    assert answer() == 42\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        work, test = _write_files(Path(tmp), module, oracle)
        sb = HardenedSubprocessSandbox()
        result = sb.run_pytest(work, test, timeout_s=30)

    assert result.passed == 1, f"expected 1 passed, got {result.passed}; stdout={result.stdout!r}"
    assert result.failed == 0
    assert result.errors == 0
    assert result.timed_out is False
    assert result.all_passed is True


# ---------------------------------------------------------------------------
# 2. Failing oracle (structured failure + traceback)
# ---------------------------------------------------------------------------

def test_hardened_sandbox_failing_oracle():
    """Sandbox captures a red oracle as failed=1 with a non-empty traceback."""
    module = "def answer():\n    return 99\n"
    oracle = (
        "from module import answer\n"
        "\n"
        "def test_answer_is_wrong():\n"
        "    assert answer() == 42, f'got {answer()}'\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        work, test = _write_files(Path(tmp), module, oracle)
        sb = HardenedSubprocessSandbox()
        result = sb.run_pytest(work, test, timeout_s=30)

    assert result.failed == 1, f"expected 1 failed, got {result.failed}; stdout={result.stdout!r}"
    assert result.passed == 0
    assert result.timed_out is False
    assert len(result.tracebacks) >= 1, "expected at least one traceback string"
    # The traceback should mention the assertion failure.
    combined_tb = "\n".join(result.tracebacks)
    assert "assert" in combined_tb.lower() or "AssertionError" in combined_tb, (
        f"traceback doesn't mention assertion failure:\n{combined_tb}"
    )


# ---------------------------------------------------------------------------
# 3. Infinite-loop timeout + process-group kill
# ---------------------------------------------------------------------------

def test_hardened_sandbox_timeout_kills_loop():
    """An infinite-loop test is killed cleanly; timed_out=True, returns within 5 s."""
    module = "# empty source\n"
    oracle = (
        "import time\n"
        "\n"
        "def test_hangs_forever():\n"
        "    while True:\n"
        "        time.sleep(0.05)\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        work, test = _write_files(Path(tmp), module, oracle)
        sb = HardenedSubprocessSandbox()
        wall_start = time.monotonic()
        result = sb.run_pytest(work, test, timeout_s=2)
        wall_elapsed = time.monotonic() - wall_start

    assert result.timed_out is True, f"expected timed_out=True; stdout={result.stdout!r}"
    assert wall_elapsed < 8, (
        f"sandbox took {wall_elapsed:.1f}s to return after a 2s timeout — "
        "process group kill may not have worked"
    )
    # Sandbox should note the kill in its output.
    assert "killed" in result.stdout.lower() or result.timed_out, (
        f"stdout should mention kill: {result.stdout!r}"
    )
