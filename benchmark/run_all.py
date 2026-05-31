"""Benchmark runner entry point.

Usage:
  python -m benchmark.run_all [--model MODEL] [--cases NAME,...] [--max-iterations N]

Model selection (model-agnostic: works with both gemini-* and claude-*):
  --model flag  >  $CODESHIFT_MODEL env var  >  config.MODEL_NAME

The runner migrates each case via the agent loop, runs the oracle under
HardenedSubprocessSandbox, then prints an aggregate scorecard.

Sandboxing: HardenedSubprocessSandbox (Phase 3a) — process-group kill on
timeout, RLIMIT_AS memory cap, trusted benchmark code only.
"""

from __future__ import annotations

import argparse
import datetime
import logging
import sys
from typing import List

from agent.llm import build_llm_client, QuotaExhaustedError
from benchmark.metadata import BAND_LABELS, BAND_ORDER, CASE_BANDS
from benchmark.runner import CaseResult, discover_cases, run_case
from config import configure_logging, resolve_model_name
from sandbox.hardened import HardenedSubprocessSandbox


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    configure_logging(level=logging.INFO)
    log = logging.getLogger("codeshift.benchmark")
    args = _parse_args(argv)

    # Model selection: CLI > env var > config default. Provider dispatched by
    # build_llm_client(), which supports claude-* (Anthropic) and gemini-*
    # (Google), making the runner model-agnostic.
    model = resolve_model_name(args.model)
    log.info("benchmark runner model=%s", model)

    case_dirs = discover_cases()
    if args.cases:
        allowed = {n.strip() for n in args.cases.split(",")}
        case_dirs = [d for d in case_dirs if d.name in allowed]
    if not case_dirs:
        print("No benchmark cases found.", file=sys.stderr)
        return 1

    try:
        llm = build_llm_client(args.model)
    except (RuntimeError, ValueError) as exc:
        print(f"Cannot initialise LLM client: {exc}", file=sys.stderr)
        return 2

    sandbox = HardenedSubprocessSandbox()
    log.info("benchmark start cases=%d sandbox=HardenedSubprocessSandbox", len(case_dirs))

    results: List[CaseResult] = []
    for case_dir in case_dirs:
        try:
            r = run_case(
                case_dir, llm, sandbox,
                max_iterations=args.max_iterations,
                test_timeout_s=args.timeout,
            )
        except QuotaExhaustedError as exc:
            completed = len(results)
            total = len(case_dirs)
            print(
                f"\n{'═' * 74}\n"
                f" QUOTA EXHAUSTED — run halted after {completed}/{total} cases\n"
                f" {exc}\n"
                f" Re-run once the quota resets (free tier: next calendar day).\n"
                f"{'═' * 74}",
                file=sys.stderr,
            )
            log.error("quota exhausted after %d/%d cases: %s", completed, total, exc)
            if results:
                print(format_scorecard(results, model=model))
                print(
                    f"\n(partial scorecard — only {completed}/{total} cases ran before quota exhaustion)",
                    file=sys.stderr,
                )
            return 3  # distinct exit code: not a pass/fail, a quota halt
        results.append(r)

    print(format_scorecard(results, model=model))

    n_pass = sum(1 for r in results if r.all_passed)
    log.info(
        "benchmark complete total=%d passed=%d pass_rate=%.1f%%",
        len(results), n_pass,
        100 * n_pass / len(results) if results else 0.0,
    )
    return 0 if all(r.all_passed for r in results) else 1


# ---------------------------------------------------------------------------
# Scorecard formatting (pure function — importable for unit tests)
# ---------------------------------------------------------------------------

def format_scorecard(results: List[CaseResult], *, model: str = "") -> str:
    """Render an aggregate scorecard string from a list of CaseResults.

    Pure function with no side-effects; importable and testable without
    any real migration or API calls.
    """
    W = 74
    sep = "═" * W
    thin = "─" * W
    date = datetime.date.today().isoformat()

    n_pass  = sum(1 for r in results if r.status == "PASS")
    n_fail  = sum(1 for r in results if r.status == "FAIL")
    n_error = sum(1 for r in results if r.status == "ERROR")
    total   = len(results)
    rate    = (100.0 * n_pass / total) if total else 0.0

    lines: List[str] = [
        sep,
        f" CodeShift Benchmark  ·  model: {model}  ·  {date}",
        sep,
        f" {'CASE':<24} {'STATUS':<8} {'ITERS':>5} {'TOKENS':>7}  {'ORACLE':>7}  {'TIME':>7}",
        thin,
    ]

    for r in results:
        oracle_str = f"{r.oracle_passed}/{r.oracle_total}"
        flag = "  ← ERROR" if r.status == "ERROR" else ""
        lines.append(
            f" {r.name:<24} {r.status:<8} {r.iterations:>5} {r.tokens:>7}"
            f"  {oracle_str:>7}  {r.duration_s:>6.1f}s{flag}"
        )

    lines += [
        thin,
        f" TOTAL: {total} cases  ·  {n_pass} PASS  ·  {n_fail} FAIL"
        + (f"  ·  {n_error} ERROR" if n_error else "")
        + f"  ·  pass rate: {rate:.1f}%",
        sep,
    ]

    # ── Per-band breakdown ────────────────────────────────────────────────
    lines += ["", f" {'BAND':<38} {'CASES':>5}  {'PASS':>4}  {'RATE':>6}", thin]
    for band in BAND_ORDER:
        label = BAND_LABELS.get(band, band)
        band_results = [r for r in results if CASE_BANDS.get(r.name, "clean") == band]
        if not band_results:
            continue
        b_total = len(band_results)
        b_pass  = sum(1 for r in band_results if r.status == "PASS")
        b_rate  = 100.0 * b_pass / b_total if b_total else 0.0
        lines.append(f" {label:<38} {b_total:>5}  {b_pass:>4}  {b_rate:>5.1f}%")
    lines += [thin, sep]

    failures = [r for r in results if r.status != "PASS"]
    if failures:
        lines += ["", f"FAILURES ({len(failures)})", thin]
        for r in failures:
            lines.append(f" {r.name}")
            lines.append(f"   migration : {r.migration_status}")
            if r.root_cause:
                # Wrap long root cause at ~68 chars
                cause = r.root_cause[:280]
                lines.append(f"   root cause: {cause}")
            lines.append("")
        lines.append(sep)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv):
    p = argparse.ArgumentParser(
        prog="benchmark.run_all",
        description="Run the CodeShift benchmark corpus and print a scorecard.",
    )
    p.add_argument(
        "--model", default=None,
        help="Model string (e.g. gemini-2.5-flash or claude-sonnet-4-6). "
             "Precedence: --model > $CODESHIFT_MODEL > config.MODEL_NAME. "
             "Provider is auto-detected from the prefix (gemini-* or claude-*).",
    )
    p.add_argument(
        "--max-iterations", type=int, default=5,
        help="Maximum repair iterations per case (default: 5).",
    )
    p.add_argument(
        "--timeout", type=int, default=30,
        help="Oracle subprocess timeout in seconds (default: 30).",
    )
    p.add_argument(
        "--cases", default=None,
        help="Comma-separated subset of case names to run (default: all).",
    )
    return p.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
