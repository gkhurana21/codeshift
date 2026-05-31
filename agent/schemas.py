"""Pydantic schemas for every agent tool.

Each of the five tools (analyze_file, read_code, transform_code, run_tests,
write_code) has an explicit input model and an explicit output model. Pinning
these schemas is the answer to v2-review item #14 - it prevents drift between
the agent's expectations and what the tool implementations return.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from analyzer.schema import Finding, Report
from sandbox.base import TestResult


# --- analyze_file ------------------------------------------------------------

class AnalyzeFileInput(BaseModel):
    path: str


class AnalyzeFileOutput(BaseModel):
    report: Report


# --- read_code ---------------------------------------------------------------

class ReadCodeInput(BaseModel):
    path: str


class ReadCodeOutput(BaseModel):
    path: str
    source: str


# --- transform_code ----------------------------------------------------------

class RepairContext(BaseModel):
    """Extra context passed during repair iterations (iter >= 2)."""

    prior_code: str = Field(..., description="The most recent migrated code that failed tests.")
    recent_tracebacks: List[str] = Field(
        default_factory=list,
        description="Up to MAX_TRACEBACKS_IN_REPAIR_PROMPT most recent failure tracebacks.",
    )
    iteration: int = Field(..., ge=2, description="1-based iteration number.")


class TokenUsage(BaseModel):
    input: int = 0
    output: int = 0

    @property
    def total(self) -> int:
        return self.input + self.output


class TransformCodeInput(BaseModel):
    source_py2: str = Field(..., description="Original Py2 source.")
    findings: List[Finding] = Field(default_factory=list)
    repair_context: Optional[RepairContext] = None

    @property
    def is_repair(self) -> bool:
        return self.repair_context is not None


class TransformCodeOutput(BaseModel):
    migrated: str = Field(..., description="Defensively-parsed Py3 source.")
    raw_response: str = Field(..., description="Untouched model response (for logs).")
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    used_corrective_retry: bool = Field(
        default=False,
        description="True if the initial output didn't parse and we did one corrective retry.",
    )


# --- run_tests ---------------------------------------------------------------

class RunTestsInput(BaseModel):
    work_dir: str
    test_path: str
    timeout_s: int = 60


class RunTestsOutput(BaseModel):
    result: TestResult


# --- write_code --------------------------------------------------------------

class WriteCodeInput(BaseModel):
    path: str
    content: str


class WriteCodeOutput(BaseModel):
    path: str
    bytes_written: int
