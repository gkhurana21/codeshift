"""The five agent tools, each with explicit Pydantic input/output schemas.

These are the building blocks the repair loop in agent/loop.py composes.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from analyzer.analyzer import analyze_file as _analyze_file
from agent.llm import LLMClient
from agent.parsing import parse_model_output
from agent.prompts import (
    SYSTEM_PROMPT,
    build_corrective_retry_prompt,
    build_initial_prompt,
    build_repair_prompt,
)
from agent.schemas import (
    AnalyzeFileInput,
    AnalyzeFileOutput,
    ReadCodeInput,
    ReadCodeOutput,
    RunTestsInput,
    RunTestsOutput,
    TokenUsage,
    TransformCodeInput,
    TransformCodeOutput,
    WriteCodeInput,
    WriteCodeOutput,
)
from sandbox.base import SandboxRunner

log = logging.getLogger("codeshift.tools")


# --- 1. analyze_file --------------------------------------------------------

def analyze_file_tool(inp: AnalyzeFileInput) -> AnalyzeFileOutput:
    """Wraps Phase 1's analyzer."""
    report = _analyze_file(inp.path)
    return AnalyzeFileOutput(report=report)


# --- 2. read_code -----------------------------------------------------------

def read_code_tool(inp: ReadCodeInput) -> ReadCodeOutput:
    p = Path(inp.path)
    return ReadCodeOutput(path=str(p), source=p.read_text(encoding="utf-8", errors="replace"))


# --- 3. transform_code ------------------------------------------------------

class TransformError(RuntimeError):
    """Raised when defensive parsing fails even after a corrective retry."""


def transform_code_tool(inp: TransformCodeInput, llm: LLMClient) -> TransformCodeOutput:
    """Build the right prompt, call the LLM, defensively parse the output,
    and retry once if the output isn't valid Py3."""
    if inp.is_repair:
        ctx = inp.repair_context
        assert ctx is not None
        user = build_repair_prompt(
            source_py2=inp.source_py2,
            findings=inp.findings,
            prior_code=ctx.prior_code,
            recent_tracebacks=ctx.recent_tracebacks,
            iteration=ctx.iteration,
        )
        mode = f"repair iter={ctx.iteration}"
    else:
        user = build_initial_prompt(source_py2=inp.source_py2, findings=inp.findings)
        mode = "initial"

    log.info("transform_code mode=%s user_chars=%d", mode, len(user))
    response = llm.invoke(SYSTEM_PROMPT, user)
    parsed = parse_model_output(response.content)

    if parsed.ok:
        return TransformCodeOutput(
            migrated=parsed.code,
            raw_response=response.content,
            token_usage=response.usage,
            used_corrective_retry=False,
        )

    # ONE corrective retry, per the v2 brief.
    log.warning("transform_code parse failed on first try: %s - retrying", parsed.parse_error)
    retry_user = (
        user
        + "\n\n---\n\n"
        + build_corrective_retry_prompt(parse_error=parsed.parse_error or "unknown")
    )
    response2 = llm.invoke(SYSTEM_PROMPT, retry_user)
    parsed2 = parse_model_output(response2.content)
    combined_usage = TokenUsage(
        input=response.usage.input + response2.usage.input,
        output=response.usage.output + response2.usage.output,
    )
    if parsed2.ok:
        return TransformCodeOutput(
            migrated=parsed2.code,
            raw_response=response2.content,
            token_usage=combined_usage,
            used_corrective_retry=True,
        )

    # Bail loudly. The loop will treat this iteration as failed.
    raise TransformError(
        f"model output still unparseable after corrective retry. "
        f"first_error={parsed.parse_error!r} retry_error={parsed2.parse_error!r}"
    )


# --- 4. run_tests -----------------------------------------------------------

def run_tests_tool(inp: RunTestsInput, sandbox: SandboxRunner) -> RunTestsOutput:
    result = sandbox.run_pytest(
        work_dir=Path(inp.work_dir),
        test_path=Path(inp.test_path),
        timeout_s=inp.timeout_s,
    )
    return RunTestsOutput(result=result)


# --- 5. write_code ----------------------------------------------------------

def write_code_tool(inp: WriteCodeInput) -> WriteCodeOutput:
    p = Path(inp.path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(inp.content, encoding="utf-8")
    return WriteCodeOutput(path=str(p), bytes_written=len(inp.content.encode("utf-8")))
