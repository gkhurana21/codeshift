"""Sandbox interface used by the agent's run_tests tool.

Phase 3 will add a hardened DockerSandbox that satisfies the same Protocol.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Protocol

from pydantic import BaseModel, Field


class TestResult(BaseModel):
    """Structured pytest result returned by every sandbox implementation."""

    passed: int = Field(..., ge=0)
    failed: int = Field(..., ge=0)
    errors: int = Field(..., ge=0)
    collected: int = Field(..., ge=0, description="Total tests collected.")
    tracebacks: List[str] = Field(
        default_factory=list,
        description="One traceback string per failing or erroring test.",
    )
    stdout: str = Field(default="", description="Raw pytest stdout (truncated).")
    duration_s: float = Field(default=0.0, ge=0.0)
    timed_out: bool = Field(default=False)

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.errors == 0 and self.collected > 0


class SandboxRunner(Protocol):
    """Anything that can run pytest against a directory + test file."""

    def run_pytest(self, work_dir: Path, test_path: Path, timeout_s: int = 60) -> TestResult:
        """Run `pytest <test_path>` from `work_dir`, return structured results.

        - `work_dir`: directory containing the code under test (added to sys.path).
        - `test_path`: path to the test file (absolute, or relative to work_dir).
        - `timeout_s`: wallclock timeout; on exceed, returns `timed_out=True`.
        """
        ...
