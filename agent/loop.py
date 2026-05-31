"""The repair loop - CodeShift's agentic heart.

Implements the v2 brief's pseudocode with all required guards:

  - defensive output parsing (in transform_code_tool)
  - best_attempt tracking (higher tests-passed wins; ties broken to earliest)
  - identical-code oscillation guard
  - repair prompt only carries the most recent 1-2 tracebacks
  - per-run token + iteration budget
  - greppable per-iteration logging:
        iter=N case=NAME passed=P failed=F action=...
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

from agent.llm import LLMClient
from agent.schemas import (
    AnalyzeFileInput,
    ReadCodeInput,
    RepairContext,
    RunTestsInput,
    TokenUsage,
    TransformCodeInput,
    WriteCodeInput,
)
from agent.tools import (
    TransformError,
    analyze_file_tool,
    read_code_tool,
    run_tests_tool,
    transform_code_tool,
    write_code_tool,
)
from analyzer.schema import Finding, Report
from config import (
    MAX_REPAIR_ITERATIONS,
    MAX_TOKENS_PER_RUN,
    MAX_TRACEBACKS_IN_REPAIR_PROMPT,
)
from sandbox.base import SandboxRunner, TestResult

log = logging.getLogger("codeshift.loop")


# --- result types ------------------------------------------------------------

class Status(str, Enum):
    OK = "OK"
    FAILED = "FAILED"
    OSCILLATION = "OSCILLATION"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    TRANSFORM_ERROR = "TRANSFORM_ERROR"


@dataclass
class Attempt:
    iteration: int
    code: str
    result: TestResult

    @property
    def pass_count(self) -> int:
        return self.result.passed

    def beats(self, other: "Attempt") -> bool:
        """Higher passed wins; ties go to the EARLIER iteration (more conservative)."""
        if self.pass_count != other.pass_count:
            return self.pass_count > other.pass_count
        # Tie-break: prefer the earlier iteration.
        return self.iteration < other.iteration


@dataclass
class MigrationResult:
    status: Status
    case_name: str
    source_path: str
    work_dir: str
    iterations_used: int
    total_tokens: int
    best_attempt: Optional[Attempt]
    final_attempt: Optional[Attempt]
    history: List[Attempt] = field(default_factory=list)
    notes: str = ""

    @property
    def all_passed(self) -> bool:
        return self.best_attempt is not None and self.best_attempt.result.all_passed


# --- main entrypoint ---------------------------------------------------------

def migrate_file(
    source_path: str | Path,
    llm: LLMClient,
    sandbox: SandboxRunner,
    test_path: str | Path | None = None,
    work_dir: str | Path | None = None,
    case_name: str | None = None,
    max_iterations: int = MAX_REPAIR_ITERATIONS,
    token_budget: int = MAX_TOKENS_PER_RUN,
    tracebacks_per_repair: int = MAX_TRACEBACKS_IN_REPAIR_PROMPT,
    test_timeout_s: int = 60,
) -> MigrationResult:
    """Migrate a single Py2 source file to Py3 with the test-feedback repair loop.

    Test discovery convention: if `test_path` is omitted, the agent looks for a
    sibling `test_<stem>.py` next to `source_path`.
    """
    source_path = Path(source_path).resolve()
    case_name = case_name or source_path.stem
    test_path = Path(test_path).resolve() if test_path else _derive_test_path(source_path)
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    if not test_path.exists():
        raise FileNotFoundError(f"sibling test file not found: {test_path}")

    work_dir, cleanup = _ensure_work_dir(work_dir, source_path, test_path)
    log.info("loop start case=%s source=%s test=%s work_dir=%s",
             case_name, source_path.name, test_path.name, work_dir)

    try:
        # 1. Analyze + read up front so each iteration shares the same baseline.
        analysis: Report = analyze_file_tool(AnalyzeFileInput(path=str(source_path))).report
        source_py2 = read_code_tool(ReadCodeInput(path=str(source_path))).source
        log.info("iter=0 case=%s analyzer findings=%d semantic=%d action=baseline_loaded",
                 case_name, len(analysis.findings),
                 sum(1 for f in analysis.findings if f.semantic_risk))

        history: List[Attempt] = []
        seen_codes: dict[str, int] = {}  # code -> iteration in which it appeared
        best: Optional[Attempt] = None
        total_tokens = 0
        status = Status.FAILED  # mutated below

        # Path the migrated code lives at inside the work_dir.
        migrated_path = work_dir / source_path.name
        test_in_work = work_dir / test_path.name

        for iteration in range(1, max_iterations + 1):
            # --- build transform input -----------------------------------------
            if iteration == 1:
                tx_input = TransformCodeInput(source_py2=source_py2, findings=analysis.findings)
            else:
                prior_attempt = history[-1]
                recent_tbs = _recent_tracebacks(history, n=tracebacks_per_repair)
                tx_input = TransformCodeInput(
                    source_py2=source_py2,
                    findings=analysis.findings,
                    repair_context=RepairContext(
                        prior_code=prior_attempt.code,
                        recent_tracebacks=recent_tbs,
                        iteration=iteration,
                    ),
                )

            # --- call the model ------------------------------------------------
            try:
                tx = transform_code_tool(tx_input, llm)
            except TransformError as e:
                log.error("iter=%d case=%s action=transform_error error=%s",
                          iteration, case_name, e)
                status = Status.TRANSFORM_ERROR
                break
            total_tokens += tx.token_usage.total

            # --- oscillation guard --------------------------------------------
            if tx.migrated in seen_codes:
                prev_iter = seen_codes[tx.migrated]
                log.warning(
                    "iter=%d case=%s action=oscillation_break "
                    "identical_to_iter=%d - stopping early",
                    iteration, case_name, prev_iter,
                )
                status = Status.OSCILLATION
                break
            seen_codes[tx.migrated] = iteration

            # --- write + run tests --------------------------------------------
            write_code_tool(WriteCodeInput(path=str(migrated_path), content=tx.migrated))
            rt_out = run_tests_tool(
                RunTestsInput(
                    work_dir=str(work_dir),
                    test_path=str(test_in_work),
                    timeout_s=test_timeout_s,
                ),
                sandbox=sandbox,
            )
            test_result = rt_out.result

            current = Attempt(iteration=iteration, code=tx.migrated, result=test_result)
            history.append(current)
            if best is None or current.beats(best):
                best = current
                best_marker = "best"
            else:
                best_marker = "no_improve"

            log.info(
                "iter=%d case=%s passed=%d failed=%d errors=%d collected=%d "
                "tokens_total=%d retry=%s action=ran_tests result=%s",
                iteration, case_name,
                test_result.passed, test_result.failed, test_result.errors,
                test_result.collected, total_tokens,
                tx.used_corrective_retry, best_marker,
            )

            # --- success? ------------------------------------------------------
            if test_result.all_passed:
                status = Status.OK
                log.info("iter=%d case=%s action=DONE all_tests_pass", iteration, case_name)
                break

            # --- budget check -------------------------------------------------
            if total_tokens >= token_budget:
                log.warning(
                    "iter=%d case=%s action=budget_exceeded total_tokens=%d budget=%d",
                    iteration, case_name, total_tokens, token_budget,
                )
                status = Status.BUDGET_EXCEEDED
                break
        else:
            # Loop fell through without break - cap hit.
            log.info("iter=%d case=%s action=cap_reached max=%d",
                     max_iterations, case_name, max_iterations)
            status = Status.FAILED if not (best and best.result.all_passed) else Status.OK

        # If best is fully green, we should report OK even when we exited due to
        # the loop ending naturally with a regressed final attempt.
        if status not in {Status.OSCILLATION, Status.TRANSFORM_ERROR, Status.BUDGET_EXCEEDED}:
            status = Status.OK if (best and best.result.all_passed) else Status.FAILED

        # On non-OK exit, restore the work_dir to the best_attempt's code so
        # downstream consumers (and the user) always see the BEST snapshot, not
        # the most recent (potentially regressed) one.
        if best is not None:
            write_code_tool(WriteCodeInput(path=str(migrated_path), content=best.code))

        result = MigrationResult(
            status=status,
            case_name=case_name,
            source_path=str(source_path),
            work_dir=str(work_dir),
            iterations_used=len(history),
            total_tokens=total_tokens,
            best_attempt=best,
            final_attempt=history[-1] if history else None,
            history=history,
            notes=_summarize_notes(status, best, history),
        )
        log.info(
            "loop end case=%s status=%s iters=%d tokens=%d best_iter=%s best_passed=%s",
            case_name, status.value, result.iterations_used, total_tokens,
            best.iteration if best else None,
            best.pass_count if best else None,
        )
        return result
    finally:
        if cleanup:
            log.info("work_dir kept at %s (not auto-cleaned)", work_dir)


# --- helpers -----------------------------------------------------------------

def _derive_test_path(source_path: Path) -> Path:
    """Convention: every foo.py has a sibling test_foo.py."""
    candidate = source_path.parent / f"test_{source_path.name}"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"No sibling test file found at {candidate}. "
        f"CodeShift's convention is foo.py + test_foo.py side-by-side."
    )


def _ensure_work_dir(
    work_dir: str | Path | None,
    source_path: Path,
    test_path: Path,
) -> tuple[Path, bool]:
    """Return (work_dir, keep_after_run).

    If the caller provided a work_dir we copy source+test into it and leave it
    alone afterwards (useful for demos). Otherwise we make a tempdir.
    """
    if work_dir is None:
        wd = Path(tempfile.mkdtemp(prefix="codeshift_work_"))
        keep = False
    else:
        wd = Path(work_dir).resolve()
        wd.mkdir(parents=True, exist_ok=True)
        keep = True
    shutil.copy2(source_path, wd / source_path.name)
    shutil.copy2(test_path, wd / test_path.name)
    return wd, keep


def _recent_tracebacks(history: List[Attempt], n: int) -> List[str]:
    """Pull the most recent n iterations' tracebacks (deduped, latest first)."""
    out: List[str] = []
    for att in reversed(history):
        for tb in att.result.tracebacks:
            if tb not in out:
                out.append(tb)
            if len(out) >= n:
                return out
    return out


def _summarize_notes(status: Status, best: Optional[Attempt], history: List[Attempt]) -> str:
    if not history:
        return "no iterations completed"
    parts = [f"status={status.value}", f"iters={len(history)}"]
    if best is not None:
        parts.append(f"best_iter={best.iteration} best_passed={best.pass_count}")
        last = history[-1]
        if last.iteration != best.iteration and last.pass_count < best.pass_count:
            parts.append(
                f"final_regressed (iter={last.iteration} passed={last.pass_count}) "
                f"-> returning best_attempt"
            )
    return " ".join(parts)
