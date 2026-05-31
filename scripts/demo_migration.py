"""Phase 2 acceptance demo (1/3): end-to-end migration with REAL Claude.

Migrates samples/migration_demo/source_py2.py using the test_feedback repair
loop. The source deliberately has the integer-division trap (test pins
sum([1,2])/2 == 1, which only works with `//` in Py3), so a naive first
migration that leaves `/` alone will fail tests and force at least one
repair iteration.

Requires ANTHROPIC_API_KEY in the environment / .env.
"""

from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from pathlib import Path

from agent.llm import LLMClient, LLMResponse, build_llm_client
from agent.loop import Status, migrate_file
from config import configure_logging, resolve_model_name
from sandbox import LocalSubprocessSandbox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "samples" / "migration_demo" / "source_py2.py"
TEST = PROJECT_ROOT / "samples" / "migration_demo" / "test_source_py2.py"


class _PromptSpy:
    """Thin wrapper that records every (system, user, response) round-trip.

    Used so the demo can quote the exact INITIAL prompt sent to Claude and the
    exact iter-1 raw response - the demo's whole point is showing whether the
    model fixed the semantic cases on the initial transform.
    """

    def __init__(self, inner: LLMClient):
        self._inner = inner
        self.calls: list[dict] = []

    def invoke(self, system: str, user: str) -> LLMResponse:
        resp = self._inner.invoke(system, user)
        self.calls.append({"system": system, "user": user, "response": resp.content})
        return resp


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="scripts.demo_migration",
                                description="Phase 2 acceptance demo with real Claude.")
    p.add_argument("--model", default=None,
                   help="Override the model (precedence: --model > $CODESHIFT_MODEL > config.MODEL_NAME).")
    p.add_argument("--max-iterations", type=int, default=5)
    p.add_argument("--show-prompt", action="store_true", default=True,
                   help="Print the exact initial prompt and iter-1 raw response.")
    return p


def main(argv: list[str] | None = None) -> int:
    configure_logging(level=logging.INFO)
    log = logging.getLogger("demo.migration")
    args = _build_argparser().parse_args(argv)

    if not SOURCE.exists() or not TEST.exists():
        log.error("missing sample files: %s, %s", SOURCE, TEST)
        return 2

    chosen_model = resolve_model_name(args.model)
    try:
        llm = build_llm_client(args.model)
    except (RuntimeError, ValueError) as e:
        log.error("cannot initialise LLM client: %s", e)
        return 2
    spy = _PromptSpy(llm)

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        log.info("=" * 70)
        log.info("DEMO 1: end-to-end migration with real Claude")
        log.info("Model  : %s", chosen_model)
        log.info("Source : %s", SOURCE)
        log.info("Test   : %s", TEST)
        log.info("Work   : %s", work)
        log.info("=" * 70)

        result = migrate_file(
            source_path=SOURCE,
            test_path=TEST,
            work_dir=work,
            llm=spy,
            sandbox=LocalSubprocessSandbox(),
            max_iterations=args.max_iterations,
            case_name="migration_demo",
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
        log.info("\n--- Migrated code (best_attempt) ---\n%s",
                 (work / SOURCE.name).read_text())
        log.info("=" * 70)

        if args.show_prompt and spy.calls:
            log.info("\n" + "=" * 70)
            log.info("EXACT INITIAL PROMPT SENT TO CLAUDE (iter 1)")
            log.info("=" * 70)
            log.info("\n--- system ---\n%s", spy.calls[0]["system"])
            log.info("\n--- user ---\n%s", spy.calls[0]["user"])
            log.info("=" * 70)
            log.info("EXACT ITER-1 RAW RESPONSE FROM CLAUDE")
            log.info("=" * 70)
            log.info("\n%s", spy.calls[0]["response"])
            log.info("=" * 70)

        if result.status == Status.OK:
            log.info("PASS: agent migrated source -> green tests in %d iteration(s)",
                     result.iterations_used)
            return 0
        log.error("FAIL: agent did not reach green tests; status=%s", result.status.value)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
