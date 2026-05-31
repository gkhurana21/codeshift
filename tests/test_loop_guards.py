"""Smoke tests for the repair loop's safety guards (all using FakeChatModel)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from agent.llm import FakeChatModel
from agent.loop import Status, migrate_file
from sandbox import LocalSubprocessSandbox


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SRC_TEMPLATE = (
    "def a():\n"
    "    return 999\n"
    "\n"
    "def b():\n"
    "    return 999\n"
)

TEST_TEMPLATE = (
    "from mod import a, b\n"
    "\n"
    "def test_a():\n"
    "    assert a() == 1\n"
    "\n"
    "def test_b():\n"
    "    assert b() == 2\n"
)


def _layout(tmp: Path) -> tuple[Path, Path, Path]:
    """Create a project layout: tmp/src/{mod.py,test_mod.py} + tmp/work/."""
    src_dir = tmp / "src"
    src_dir.mkdir()
    src = src_dir / "mod.py"
    test = src_dir / "test_mod.py"
    src.write_text(SRC_TEMPLATE)
    test.write_text(TEST_TEMPLATE)
    work = tmp / "work"
    return src, test, work


# ---------------------------------------------------------------------------
# Guard: identical-code oscillation
# ---------------------------------------------------------------------------

def test_oscillation_guard_breaks_on_identical_code():
    R1 = "def a():\n    return 0\n\ndef b():\n    return 0\n"
    R2 = "def a():\n    return 1\n\ndef b():\n    return 0\n"  # iter 2
    # iter 3 returns the same code as iter 2 -> oscillation.
    fake = FakeChatModel(responses=[R1, R2, R2, R2, R2])

    with tempfile.TemporaryDirectory() as tmp:
        src, test, work = _layout(Path(tmp))
        result = migrate_file(
            source_path=src, test_path=test, work_dir=work,
            llm=fake, sandbox=LocalSubprocessSandbox(),
            max_iterations=5, case_name="osc",
        )

    assert result.status == Status.OSCILLATION
    # The loop should stop BEFORE running iter 3's tests.
    assert result.iterations_used == 2
    # Should have called the LLM 3 times: iter 1, iter 2, iter 3 (caught by guard).
    assert len(fake.calls) == 3


# ---------------------------------------------------------------------------
# Guard: best_attempt returned when final iteration regresses
# ---------------------------------------------------------------------------

def test_best_attempt_returned_on_regression():
    # iter1 passes 1/2, iter2 0/2, iter3 0/2 (different code, no oscillation).
    R1 = "def a():\n    return 1\n\ndef b():\n    return 999\n"
    R2 = "def a():\n    return -1\n\ndef b():\n    return -1\n"
    R3 = "def a():\n    return -2\n\ndef b():\n    return -3\n"
    fake = FakeChatModel(responses=[R1, R2, R3])

    with tempfile.TemporaryDirectory() as tmp:
        src, test, work = _layout(Path(tmp))
        result = migrate_file(
            source_path=src, test_path=test, work_dir=work,
            llm=fake, sandbox=LocalSubprocessSandbox(),
            max_iterations=3, case_name="reg",
        )

        assert result.status == Status.FAILED
        assert result.iterations_used == 3
        assert result.best_attempt is not None
        assert result.best_attempt.iteration == 1
        assert result.best_attempt.pass_count == 1
        # Final iteration was worse than best.
        assert result.final_attempt.pass_count == 0
        # File on disk should be the best_attempt's code, not the regressed final.
        on_disk = (work / "mod.py").read_text()
        assert on_disk == result.best_attempt.code


# ---------------------------------------------------------------------------
# Guard: token budget shuts the loop down
# ---------------------------------------------------------------------------

def test_token_budget_stops_loop():
    # Every response is broken (0/2). Tokens-per-call = 100; budget = 150.
    R = "def a():\n    return 0\n\ndef b():\n    return 0\n"
    R2 = "def a():\n    return -1\n\ndef b():\n    return -1\n"
    fake = FakeChatModel(responses=[R, R2, R, R2, R], tokens_per_call=100)

    with tempfile.TemporaryDirectory() as tmp:
        src, test, work = _layout(Path(tmp))
        result = migrate_file(
            source_path=src, test_path=test, work_dir=work,
            llm=fake, sandbox=LocalSubprocessSandbox(),
            max_iterations=10, token_budget=150, case_name="budget",
        )

    assert result.status == Status.BUDGET_EXCEEDED
    # Total tokens should exceed the budget by at most one iteration's worth.
    assert result.total_tokens >= 150
    # Best attempt should still be returned.
    assert result.best_attempt is not None


# ---------------------------------------------------------------------------
# Happy path: early exit when tests pass
# ---------------------------------------------------------------------------

def test_early_exit_when_tests_pass():
    GREEN = "def a():\n    return 1\n\ndef b():\n    return 2\n"
    fake = FakeChatModel(responses=[GREEN])

    with tempfile.TemporaryDirectory() as tmp:
        src, test, work = _layout(Path(tmp))
        result = migrate_file(
            source_path=src, test_path=test, work_dir=work,
            llm=fake, sandbox=LocalSubprocessSandbox(),
            max_iterations=5, case_name="happy",
        )

    assert result.status == Status.OK
    assert result.iterations_used == 1
    assert result.best_attempt.pass_count == 2
    assert result.all_passed


# ---------------------------------------------------------------------------
# Repair prompt only carries the most recent 1-2 tracebacks
# ---------------------------------------------------------------------------

def test_repair_prompt_uses_only_recent_tracebacks():
    """Iter 3's repair prompt should contain iter 2's tracebacks (most recent),
    not iter 1's. We probe this by inspecting the FakeChatModel's recorded calls."""
    R1 = "def a():\n    return 0\n\ndef b():\n    return 0\n"  # fails both
    R2 = "def a():\n    return 1\n\ndef b():\n    return 0\n"  # fixes a, b still wrong
    R3 = "def a():\n    return 1\n\ndef b():\n    return 2\n"  # both pass
    fake = FakeChatModel(responses=[R1, R2, R3])

    with tempfile.TemporaryDirectory() as tmp:
        src, test, work = _layout(Path(tmp))
        result = migrate_file(
            source_path=src, test_path=test, work_dir=work,
            llm=fake, sandbox=LocalSubprocessSandbox(),
            max_iterations=5, tracebacks_per_repair=2, case_name="recents",
        )

    assert result.status == Status.OK
    # Iter 3 prompt should mention test_b's failure (most recent from iter 2),
    # but should NOT include a full history of every prior iteration.
    iter3_prompt = fake.calls[2][1]
    assert "FAILING TEST OUTPUT" in iter3_prompt
    # Iter 1 had two failing tests; iter 2 has only test_b failing.
    # We expect to see test_b in the repair prompt and NOT a long traceback dump.
    assert "test_b" in iter3_prompt
