"""Phase 2 acceptance demo (1/3, scripted variant).

Equivalent to scripts/demo_migration.py but uses FakeChatModel with scripted
"Claude-like" responses, so it runs without ANTHROPIC_API_KEY. Demonstrates
the SAME control flow:

  iter 1: a near-correct migration that leaves `/` where Py2 used `//`,
          plus a few other small bugs - tests fail.
  iter 2: a repair that fixes the integer-division bug after reading the
          traceback - all tests pass.

For the real-Claude version, set ANTHROPIC_API_KEY and run scripts/demo_migration.

This intentionally migrates samples/migration_demo/source_py2.py (the same
hand-written Py2 file used for the real demo), so the test_behavior is real
and ending green proves the loop actually worked.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from agent.llm import FakeChatModel
from agent.loop import Status, migrate_file
from config import configure_logging
from sandbox import LocalSubprocessSandbox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "samples" / "migration_demo" / "source_py2.py"
TEST = PROJECT_ROOT / "samples" / "migration_demo" / "test_source_py2.py"


# Iter 1: a near-correct migration but with `sum/len` instead of `sum//len`.
# The integer-division test (`average([1,2]) == 1`) will fail because in Py3,
# 3/2 == 1.5 not 1. Everything else is correct.
ITER1_RESPONSE = '''\
def average(numbers):
    """Mean of a list of integers - Py2 returns an integer (floor)."""
    return sum(numbers) / len(numbers)


def first_key(d):
    """Return the first key from a dict - Py2 dict.keys() is a list, Py3 is a view."""
    return list(d.keys())[0]


def shout(s):
    """Uppercase a string. Py2 must accept both str and unicode."""
    if isinstance(s, str):
        return str(s).upper()
    raise TypeError("expected string")


def has(d, k):
    """Membership check - Py2 idiom."""
    return k in d


from functools import reduce


class Adder:
    """Sum *args plus a base, using the Py2 reduce() builtin."""

    def __init__(self, base):
        self.base = base

    def add(self, *args):
        return reduce(lambda a, b: a + b, args, self.base)


def counts(words):
    """Count word occurrences. Uses iteritems for iteration."""
    out = {}
    for w in words:
        out[w] = out.get(w, 0) + 1
    pairs = []
    for k, v in out.items():
        pairs.append((k, v))
    return pairs
'''


# Iter 2: the repair. The agent has seen the traceback for
# test_average_preserves_int_division and corrects `/` to `//`.
# Also returns int explicitly to satisfy the isinstance(..., int) check.
ITER2_RESPONSE = '''\
def average(numbers):
    """Mean of a list of integers - Py2 returns an integer (floor)."""
    return sum(numbers) // len(numbers)


def first_key(d):
    """Return the first key from a dict - Py2 dict.keys() is a list, Py3 is a view."""
    return list(d.keys())[0]


def shout(s):
    """Uppercase a string. Py2 must accept both str and unicode."""
    if isinstance(s, str):
        return str(s).upper()
    raise TypeError("expected string")


def has(d, k):
    """Membership check - Py2 idiom."""
    return k in d


from functools import reduce


class Adder:
    """Sum *args plus a base, using the Py2 reduce() builtin."""

    def __init__(self, base):
        self.base = base

    def add(self, *args):
        return reduce(lambda a, b: a + b, args, self.base)


def counts(words):
    """Count word occurrences. Uses iteritems for iteration."""
    out = {}
    for w in words:
        out[w] = out.get(w, 0) + 1
    pairs = []
    for k, v in out.items():
        pairs.append((k, v))
    return pairs
'''


def main() -> int:
    configure_logging(level=logging.INFO)
    log = logging.getLogger("demo.migration_scripted")

    if not SOURCE.exists() or not TEST.exists():
        log.error("missing sample files: %s, %s", SOURCE, TEST)
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # Copy source+test into a per-run dir; migrate_file will then re-copy
        # into its own work_dir. We use a stable named work_dir so we can show
        # the final migrated code on disk.
        work = tmp_path / "work"

        log.info("=" * 70)
        log.info("DEMO 1 (scripted): end-to-end migration with FakeChatModel")
        log.info("Source : %s", SOURCE)
        log.info("Test   : %s", TEST)
        log.info("Work   : %s", work)
        log.info("")
        log.info("Scripted scenario:")
        log.info("  iter 1: realistic Claude-like migration that misses the")
        log.info("          integer-division semantic (uses / instead of //)")
        log.info("          => test_average_preserves_int_division FAILS")
        log.info("  iter 2: repair prompt carries the traceback; agent")
        log.info("          changes / to // => ALL tests pass")
        log.info("=" * 70)

        fake = FakeChatModel(responses=[ITER1_RESPONSE, ITER2_RESPONSE])
        result = migrate_file(
            source_path=SOURCE,
            test_path=TEST,
            work_dir=work,
            llm=fake,
            sandbox=LocalSubprocessSandbox(),
            max_iterations=5,
            case_name="migration_demo_scripted",
        )

        log.info("=" * 70)
        log.info("RESULT")
        log.info("  status         : %s", result.status.value)
        log.info("  iterations_used: %d", result.iterations_used)
        log.info("  total tokens   : %d", result.total_tokens)
        if result.best_attempt:
            b = result.best_attempt
            log.info("  best_attempt   : iter=%d passed=%d failed=%d errors=%d",
                     b.iteration, b.pass_count, b.result.failed, b.result.errors)
        log.info("  notes          : %s", result.notes)
        log.info("=" * 70)
        log.info("Per-iteration outcomes:")
        for att in result.history:
            log.info("  iter=%d passed=%d failed=%d errors=%d collected=%d",
                     att.iteration, att.pass_count, att.result.failed,
                     att.result.errors, att.result.collected)
        log.info("=" * 70)

        on_disk_path = work / SOURCE.name
        log.info("Final migrated file on disk -> %s", on_disk_path)
        log.info("\n%s", on_disk_path.read_text())
        log.info("=" * 70)

        # Acceptance: must end green.
        assert result.status == Status.OK, (
            f"acceptance failed: status={result.status.value}, expected OK"
        )
        assert result.best_attempt is not None and result.best_attempt.result.all_passed, (
            "acceptance failed: best_attempt should be fully green"
        )
        assert result.iterations_used >= 2, (
            f"acceptance demo should require at least one repair iter; used={result.iterations_used}"
        )
        log.info("PASS: agent went from %d/%d -> %d/%d in %d iteration(s)",
                 result.history[0].pass_count,
                 result.history[0].result.collected,
                 result.best_attempt.pass_count,
                 result.best_attempt.result.collected,
                 result.iterations_used)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
