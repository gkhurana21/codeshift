"""Phase 2 acceptance demo (3/3): best_attempt returned when final regresses.

Scripted scenario:
  iter 1: passes 1/2  (this is the best we'll ever see)
  iter 2: passes 0/2  (regression)
  iter 3: passes 0/2  (different code, still regressed)
  cap reached -> status=FAILED, best_attempt must be iter 1.

Also verifies the loop WRITES BACK the best_attempt's code to disk so the
caller never sees a worse-than-best snapshot.
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


# Iter 1: a() correct, b() wrong -> 1/2 passes. BEST.
RESPONSE_ITER1 = (
    "def a():\n"
    "    return 1\n"
    "\n"
    "def b():\n"
    "    return 999\n"
)

# Iter 2: both wrong -> 0/2 (regression from iter 1).
RESPONSE_ITER2 = (
    "def a():\n"
    "    return -1\n"
    "\n"
    "def b():\n"
    "    return -1\n"
)

# Iter 3: still both wrong, but different values -> 0/2 (still regressed).
RESPONSE_ITER3 = (
    "def a():\n"
    "    return -2\n"
    "\n"
    "def b():\n"
    "    return -3\n"
)


def main() -> int:
    configure_logging(level=logging.INFO)
    log = logging.getLogger("demo.regression")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "src" / "mod.py"
        test = tmp_path / "src" / "test_mod.py"
        src.parent.mkdir(parents=True)
        src.write_text(SOURCE_PY2)
        test.write_text(TEST_PY)
        work = tmp_path / "work"

        log.info("=" * 70)
        log.info("DEMO 3: best_attempt returned when the final iteration regresses")
        log.info("Scripted responses:")
        log.info("  iter 1 -> passes 1/2  (this should become best_attempt)")
        log.info("  iter 2 -> passes 0/2  (regression)")
        log.info("  iter 3 -> passes 0/2  (further regression)")
        log.info("Cap=3 -> expect status=FAILED, best_attempt.iteration=1")
        log.info("=" * 70)

        fake = FakeChatModel(responses=[RESPONSE_ITER1, RESPONSE_ITER2, RESPONSE_ITER3])
        result = migrate_file(
            source_path=src,
            test_path=test,
            work_dir=work,
            llm=fake,
            sandbox=LocalSubprocessSandbox(),
            max_iterations=3,
            case_name="regression_demo",
        )

        log.info("=" * 70)
        log.info("RESULT")
        log.info("  status         : %s", result.status.value)
        log.info("  iterations_used: %d", result.iterations_used)
        if result.best_attempt:
            b = result.best_attempt
            log.info("  best_attempt   : iter=%d passed=%d failed=%d",
                     b.iteration, b.pass_count, b.result.failed)
        if result.final_attempt:
            f = result.final_attempt
            log.info("  final_attempt  : iter=%d passed=%d failed=%d",
                     f.iteration, f.pass_count, f.result.failed)
        log.info("  notes          : %s", result.notes)
        log.info("=" * 70)

        # Acceptance checks
        assert result.status == Status.FAILED, f"expected FAILED, got {result.status}"
        assert result.iterations_used == 3, f"expected 3 iters, got {result.iterations_used}"
        assert result.best_attempt is not None
        assert result.best_attempt.iteration == 1, (
            f"best_attempt should be iter 1 (1/2 passes), got iter {result.best_attempt.iteration}"
        )
        assert result.best_attempt.pass_count == 1, (
            f"best_attempt.pass_count should be 1, got {result.best_attempt.pass_count}"
        )
        assert result.final_attempt.iteration == 3
        assert result.final_attempt.pass_count == 0, "final iter should have regressed to 0 passes"
        assert result.best_attempt.pass_count > result.final_attempt.pass_count, (
            "best_attempt should strictly beat final"
        )

        # And the file on disk should be the best_attempt's code, not the regressed one.
        on_disk = (work / "mod.py").read_text()
        assert on_disk == result.best_attempt.code, (
            "loop did not write best_attempt back to disk after regression"
        )

        log.info("PASS: best_attempt (iter=1, 1/2 passes) returned even though "
                 "final iter regressed to 0/2; best snapshot also restored on disk.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
