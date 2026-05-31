"""CLI: `python -m agent.migrate path/to/source.py [--test path/to/test_*.py] [--work-dir DIR]`

Runs the full Phase 2 repair loop against a real Anthropic Claude model.
Requires ANTHROPIC_API_KEY in the environment / .env.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent.llm import build_llm_client
from agent.loop import Status, migrate_file
from config import MAX_REPAIR_ITERATIONS, MAX_TOKENS_PER_RUN, configure_logging, resolve_model_name
from sandbox import LocalSubprocessSandbox


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    p = argparse.ArgumentParser(prog="agent.migrate", description="Migrate a Py2 file to Py3 with a test-feedback repair loop.")
    p.add_argument("source", help="Path to the Py2 source file.")
    p.add_argument("--model", default=None,
                   help="Model id (precedence: --model > $CODESHIFT_MODEL > config.MODEL_NAME). "
                        "Prefix selects backend: claude-* -> Anthropic, gemini-* -> Gemini.")
    p.add_argument("--test", default=None, help="Path to the pytest file. Default: sibling test_<source>.py")
    p.add_argument("--work-dir", default=None, help="Directory to copy source+test into and migrate. Default: tempdir.")
    p.add_argument("--max-iterations", type=int, default=MAX_REPAIR_ITERATIONS)
    p.add_argument("--token-budget", type=int, default=MAX_TOKENS_PER_RUN)
    p.add_argument("--timeout-s", type=int, default=60, help="Pytest wallclock timeout per iteration.")
    args = p.parse_args(argv)

    source = Path(args.source)
    if not source.exists():
        print(f"error: source not found: {source}", file=sys.stderr)
        return 2

    try:
        llm = build_llm_client(args.model)
    except (RuntimeError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    result = migrate_file(
        source_path=source,
        test_path=args.test,
        work_dir=args.work_dir,
        llm=llm,
        sandbox=LocalSubprocessSandbox(),
        max_iterations=args.max_iterations,
        token_budget=args.token_budget,
        test_timeout_s=args.timeout_s,
    )

    print()
    print("=== Migration result ===")
    print(f"model           : {resolve_model_name(args.model)}")
    print(f"case            : {result.case_name}")
    print(f"status          : {result.status.value}")
    print(f"iterations used : {result.iterations_used}")
    print(f"total tokens    : {result.total_tokens}")
    if result.best_attempt:
        b = result.best_attempt
        print(f"best attempt    : iter={b.iteration} passed={b.pass_count} failed={b.result.failed} errors={b.result.errors}")
    print(f"work dir        : {result.work_dir}")
    print(f"notes           : {result.notes}")
    return 0 if result.status == Status.OK else 1


if __name__ == "__main__":
    raise SystemExit(main())
