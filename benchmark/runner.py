"""Core benchmark runner: migrate one case and return a structured result.

Each case directory must contain:
  source_py2.py   - the Python 2 source to migrate
  test_behavior.py - the behavioral oracle (encodes correct Py2-equivalent Py3 behavior)

The oracle IS the test_feedback file passed to migrate_file; a case passes iff
the oracle turns green after migration.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from agent.llm import LLMClient, QuotaExhaustedError
from agent.loop import migrate_file
from sandbox.base import SandboxRunner

log = logging.getLogger("codeshift.benchmark")

# Canonical cases directory, relative to this file.
CASES_DIR: Path = Path(__file__).resolve().parent / "cases"


@dataclass
class CaseResult:
    """Structured result for a single benchmark case."""

    name: str
    status: str            # "PASS" | "FAIL" | "ERROR"
    migration_status: str  # agent loop Status.value, or "ERROR" on runner exception
    oracle_passed: int
    oracle_failed: int
    oracle_total: int
    iterations: int
    tokens: int
    root_cause: str        # non-empty on FAIL or ERROR; first traceback excerpt
    duration_s: float

    @property
    def all_passed(self) -> bool:
        return self.status == "PASS"


def run_case(
    case_dir: Path,
    llm: LLMClient,
    sandbox: SandboxRunner,
    *,
    max_iterations: int = 5,
    test_timeout_s: int = 30,
) -> CaseResult:
    """Migrate one case and run its behavioral oracle.

    Returns a CaseResult regardless of outcome; never raises.
    """
    name = case_dir.name
    source = case_dir / "source_py2.py"
    oracle = case_dir / "test_behavior.py"

    if not source.exists() or not oracle.exists():
        return CaseResult(
            name=name, status="ERROR", migration_status="ERROR",
            oracle_passed=0, oracle_failed=0, oracle_total=0,
            iterations=0, tokens=0,
            root_cause=f"missing source_py2.py or test_behavior.py in {case_dir}",
            duration_s=0.0,
        )

    log.info("benchmark case=%s starting source=%s", name, source.name)
    wall_start = time.monotonic()

    try:
        result = migrate_file(
            source_path=source,
            test_path=oracle,
            llm=llm,
            sandbox=sandbox,
            case_name=name,
            max_iterations=max_iterations,
            test_timeout_s=test_timeout_s,
        )
    except QuotaExhaustedError:
        # Propagate immediately — the benchmark runner main loop catches this
        # and halts the whole run with a clean "quota exhausted after N cases"
        # message rather than burning the remaining quota on subsequent cases.
        raise
    except Exception as exc:
        duration = round(time.monotonic() - wall_start, 2)
        log.error("benchmark case=%s runner exception: %s", name, exc)
        return CaseResult(
            name=name, status="ERROR", migration_status="ERROR",
            oracle_passed=0, oracle_failed=0, oracle_total=0,
            iterations=0, tokens=0,
            root_cause=f"runner exception: {type(exc).__name__}: {exc}",
            duration_s=duration,
        )

    duration = round(time.monotonic() - wall_start, 2)
    best = result.best_attempt
    oracle_passed = best.result.passed if best else 0
    oracle_failed = best.result.failed if best else 0
    oracle_total = best.result.collected if best else 0

    status = "PASS" if result.all_passed else "FAIL"
    root_cause = ""
    if status != "PASS":
        if best and best.result.tracebacks:
            # First traceback, flattened for the table row
            root_cause = best.result.tracebacks[0][:300].replace("\n", " | ")
        else:
            root_cause = f"migration status: {result.status.value}"

    log.info(
        "benchmark case=%s status=%s migration=%s iters=%d tokens=%d "
        "oracle=%d/%d duration=%.1fs",
        name, status, result.status.value,
        result.iterations_used, result.total_tokens,
        oracle_passed, oracle_total, duration,
    )
    return CaseResult(
        name=name,
        status=status,
        migration_status=result.status.value,
        oracle_passed=oracle_passed,
        oracle_failed=oracle_failed,
        oracle_total=oracle_total,
        iterations=result.iterations_used,
        tokens=result.total_tokens,
        root_cause=root_cause,
        duration_s=duration,
    )


def discover_cases(cases_dir: Optional[Path] = None) -> List[Path]:
    """Return sorted list of case directories that have both required files."""
    root = cases_dir or CASES_DIR
    return sorted(
        p for p in root.iterdir()
        if p.is_dir()
        and (p / "source_py2.py").exists()
        and (p / "test_behavior.py").exists()
    )
