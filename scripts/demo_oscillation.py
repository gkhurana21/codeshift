"""Phase 2 acceptance demo (2/3): the oscillation guard.

Uses FakeChatModel to script a scenario where the model keeps emitting an
identical "fix" across iterations. The loop must detect this and break early
with status=OSCILLATION rather than burning the full iteration budget.

This deliberately uses NO API key - the demo is purely about the control
flow guard, not LLM quality.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from agent.llm import FakeChatModel
from agent.loop import Status, migrate_file
from config import configure_logging
from sandbox import LocalSubprocessSandbox


SOURCE_PY2 = (
    "def a():\n"
    "    return 999\n"
    "\n"
    "def b():\n"
    "    return 999\n"
)

TEST_PY = (
    "from mod import a, b\n"
    "\n"
    "def test_a():\n"
    "    assert a() == 1\n"
    "\n"
    "def test_b():\n"
    "    assert b() == 2\n"
)


# Iter 1: a different first attempt (0/2).
RESPONSE_1 = (
    "def a():\n"
    "    return 0\n"
    "\n"
    "def b():\n"
    "    return 0\n"
)

# Iter 2 + Iter 3: the model emits the SAME repair both times.
RESPONSE_REPEATED = (
    "def a():\n"
    "    return 99\n"
    "\n"
    "def b():\n"
    "    return 88\n"
)


def main() -> int:
    configure_logging(level=logging.INFO)
    log = logging.getLogger("demo.oscillation")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "src" / "mod.py"
        test = tmp_path / "src" / "test_mod.py"
        src.parent.mkdir(parents=True)
        src.write_text(SOURCE_PY2)
        test.write_text(TEST_PY)
        work = tmp_path / "work"

        log.info("=" * 70)
        log.info("DEMO 2: oscillation guard")
        log.info("Scripted responses:")
        log.info("  iter 1 -> distinct broken code")
        log.info("  iter 2 -> attempted fix (still broken)")
        log.info("  iter 3 -> IDENTICAL to iter 2's code -> oscillation expected")
        log.info("=" * 70)

        fake = FakeChatModel(responses=[RESPONSE_1, RESPONSE_REPEATED, RESPONSE_REPEATED, RESPONSE_REPEATED])
        result = migrate_file(
            source_path=src,
            test_path=test,
            work_dir=work,
            llm=fake,
            sandbox=LocalSubprocessSandbox(),
            max_iterations=5,
            case_name="oscillation_demo",
        )

        log.info("=" * 70)
        log.info("RESULT")
        log.info("  status         : %s", result.status.value)
        log.info("  iterations_used: %d", result.iterations_used)
        log.info("  llm calls      : %d", len(fake.calls))
        if result.best_attempt:
            b = result.best_attempt
            log.info("  best_attempt   : iter=%d passed=%d failed=%d",
                     b.iteration, b.pass_count, b.result.failed)
        log.info("=" * 70)

        # Acceptance check
        assert result.status == Status.OSCILLATION, (
            f"expected OSCILLATION status, got {result.status}"
        )
        assert result.iterations_used < 5, (
            f"loop should have stopped before the cap; ran {result.iterations_used} iters"
        )
        log.info("PASS: oscillation guard fired (status=OSCILLATION, "
                 "stopped after %d iterations < cap=5)", result.iterations_used)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
