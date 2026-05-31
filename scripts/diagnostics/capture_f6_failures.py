"""Diagnostic: capture migrated output for F6 failure cases at temperature=0.

PURPOSE
-------
This is a one-time evidence-capture script, not a regular test runner.
It re-runs the two benchmark cases that fail due to F6 (missing `from None`
on exception re-raises) with an explicit work_dir so the migrated source is
preserved after the run for inspection.

Temperature=0 makes the output deterministic — the result is identical to the
original benchmark run. This is evidence retrieval for a fixed result, not
a re-roll of the benchmark.

BACKGROUND
----------
Both error_translator and validation_chain fail because the LLM correctly
converts `except E, e:` → `except E as e:` but does NOT add `from None` to
re-raises. This means `__context__` is set on the re-raised exception, which
the oracle asserts must be None.

The finding is consistent across Gemini 2.5 Flash and Claude Sonnet 4.6 —
two models from different providers produce byte-identical migrated output
for both cases. See README.md Results → Cross-model comparison.

USAGE
-----
Run from the project root:
    .venv/bin/python scripts/diagnostics/capture_f6_failures.py

Requires ANTHROPIC_API_KEY in .env or environment.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

from agent.llm import build_llm_client
from agent.loop import migrate_file
from sandbox.hardened import HardenedSubprocessSandbox

CASES_DIR = Path("benchmark/cases")
CASES = ["error_translator", "validation_chain"]


def main() -> None:
    llm = build_llm_client(model="claude-sonnet-4-6", temperature=0.0, max_tokens=4096)
    sandbox = HardenedSubprocessSandbox()

    for case_name in CASES:
        case_dir = CASES_DIR / case_name
        source = case_dir / "source_py2.py"
        oracle = case_dir / "test_behavior.py"

        # Explicit work_dir → kept after run so we can read the migrated file.
        work_dir = Path(tempfile.mkdtemp(prefix=f"capture_{case_name}_"))

        print(f"\n{'═' * 70}")
        print(f" CASE: {case_name}  →  work_dir: {work_dir}")
        print(f"{'═' * 70}")

        result = migrate_file(
            source_path=source,
            test_path=oracle,
            llm=llm,
            sandbox=sandbox,
            case_name=case_name,
            max_iterations=5,
            test_timeout_s=30,
            work_dir=work_dir,
        )

        migrated_path = work_dir / source.name
        print(f"\n── Migrated source ({migrated_path.name}) ──")
        print(migrated_path.read_text())

        print(
            f"\n── Loop result: status={result.status.value}"
            f"  iters={result.iterations_used}"
            f"  tokens={result.total_tokens} ──"
        )
        best = result.best_attempt
        if best:
            print(f"   best iter: passed={best.result.passed}/{best.result.collected}")

        # Full verbose traceback so the exact __context__ assertion is visible.
        print(f"\n── pytest output (verbose) ──")
        proc = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                str(work_dir / "test_behavior.py"),
                "-v", "--tb=long", "--no-header",
            ],
            capture_output=True,
            text=True,
        )
        print(proc.stdout)
        if proc.stderr:
            print("STDERR:", proc.stderr[:500])


if __name__ == "__main__":
    main()
