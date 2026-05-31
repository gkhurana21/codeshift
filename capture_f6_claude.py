"""Capture diagnostic: re-run F6 failure cases with Claude at temperature=0.

Passes an explicit work_dir to migrate_file so the migrated source is preserved
after the run. Temperature=0 makes this deterministic — identical to the
original benchmark run (which also used temperature=0).

Usage:
    .venv/bin/python capture_f6_claude.py
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

llm = build_llm_client(model="claude-sonnet-4-6", temperature=0.0, max_tokens=4096)
sandbox = HardenedSubprocessSandbox()

for case_name in CASES:
    case_dir = CASES_DIR / case_name
    source = case_dir / "source_py2.py"
    oracle = case_dir / "test_behavior.py"

    # Keep the work dir so we can read the migrated file
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
    print(f"\n── Migrated source ({migrated_path}) ──")
    print(migrated_path.read_text())

    print(f"\n── Loop result: status={result.status.value}  iters={result.iterations_used}  tokens={result.total_tokens} ──")
    best = result.best_attempt
    if best:
        print(f"   best iter: passed={best.result.passed}/{best.result.collected}")

    # Run pytest directly so we get the full verbose traceback
    print(f"\n── pytest output (verbose) ──")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(work_dir / "test_behavior.py"),
         "-v", "--tb=long", "--no-header"],
        capture_output=True, text=True,
    )
    print(proc.stdout)
    if proc.stderr:
        print("STDERR:", proc.stderr[:500])
