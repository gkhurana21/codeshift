"""Prompt construction for the migration agent.

Two distinct templates per v2-review item #6:

  * INITIAL  - analysis JSON + Py2 code -> Py3 code (first attempt).
  * REPAIR   - prior Py3 code + most-recent traceback(s) -> targeted fix.

The user's brief is explicit that mechanical findings should be flagged as
straightforward rewrites and semantic-risk findings called out as requiring
careful behavior-preserving reasoning. Both prompts surface that distinction.
"""

from __future__ import annotations

from typing import List

from analyzer.schema import Category, Finding


# --- system / role-setting ---------------------------------------------------

SYSTEM_PROMPT = """You are CodeShift, a meticulous Python 2 -> Python 3 migration tool.

Your only job: read Python 2 source and produce a Python 3 version that
preserves runtime behavior, then satisfies the existing test suite.

Output discipline (non-negotiable):
- Return ONLY the migrated Python 3 source. No prose. No markdown fences.
  No "Here is the code:" preamble. Just code.
- The output MUST parse as valid Python 3 with ast.parse(...). It will be
  checked and you will be asked to retry if it does not.
- Do not add or remove dependencies. Use only stdlib unless the original
  already imported a third-party package.
- Do not rename public symbols, change function signatures, or alter docstrings
  unless required to migrate.
"""


# --- finding rendering -------------------------------------------------------

def _render_findings_block(findings: List[Finding]) -> str:
    """Group findings into SEMANTIC-RISK (call out carefully) vs MECHANICAL."""
    if not findings:
        return "No Py2 constructs were detected. Migration should be near-trivial."

    semantic = [f for f in findings if f.semantic_risk]
    stdlib = [f for f in findings if not f.semantic_risk and f.category == Category.STDLIB]
    mechanical = [
        f for f in findings
        if not f.semantic_risk and f.category != Category.STDLIB and f.category != Category.META
    ]

    lines: List[str] = []

    if semantic:
        lines.append("=== SEMANTIC RISK (behavior-changing - reason carefully) ===")
        lines.append(
            "These items can SILENTLY change runtime behavior, not just syntax. "
            "For each, think about what the Py2 semantics were and ensure the Py3 "
            "version produces the same observable results."
        )
        for f in semantic:
            lines.append(
                f"  L{f.line:>3}:{f.column:<2}  {f.construct_type:<32}  {f.snippet}"
            )
            if f.notes:
                lines.append(f"            note: {f.notes}")
        lines.append("")

    if stdlib:
        lines.append("=== STDLIB REORGANIZATION (mechanical but multi-step) ===")
        lines.append(
            "Apply the documented Py3 equivalents. Update imports AND all call sites."
        )
        for f in stdlib:
            lines.append(
                f"  L{f.line:>3}:{f.column:<2}  {f.construct_type:<32}  {f.snippet}"
            )
            if f.notes:
                lines.append(f"            -> {f.notes}")
        lines.append("")

    if mechanical:
        lines.append("=== MECHANICAL REWRITES (straightforward) ===")
        for f in mechanical:
            note = f" ({f.notes})" if f.notes else ""
            lines.append(
                f"  L{f.line:>3}:{f.column:<2}  {f.construct_type:<32}  {f.snippet}{note}"
            )
        lines.append("")

    return "\n".join(lines).rstrip()


# --- INITIAL prompt ----------------------------------------------------------

INITIAL_TEMPLATE = """Migrate this Python 2 source file to Python 3.

Static analysis findings from CodeShift's parso-based analyzer:

{findings_block}

Original Python 2 source:

{source}

Remember:
- Output ONLY the migrated Python 3 source. No fences, no commentary.
- Preserve behavior. For SEMANTIC RISK items, the analyzer's notes tell you
  exactly which trap to watch for (e.g. integer division, dict views,
  iterator-returning map/filter/zip).
- Tests will be run against your output. You will get failure tracebacks if
  any test fails, and you will be asked to fix them iteratively.
"""


def build_initial_prompt(source_py2: str, findings: List[Finding]) -> str:
    return INITIAL_TEMPLATE.format(
        findings_block=_render_findings_block(findings),
        source=source_py2.rstrip() + "\n",
    )


# --- REPAIR prompt -----------------------------------------------------------

REPAIR_TEMPLATE = """The last migration attempt failed tests. Fix the specific failures listed below.

YOUR PREVIOUS MIGRATED CODE (this is what failed):

{prior_code}

FAILING TEST OUTPUT (only the most recent {n_tracebacks} failure(s) shown):

{tracebacks_block}

ANALYZER FINDINGS (for reference - the same ones from iteration 1):

{findings_block}

Fix instructions:
- Make the MINIMUM change required to fix the failing tests. Do not refactor
  unrelated code.
- If a failure indicates a SEMANTIC RISK was migrated incorrectly (e.g. you
  used `/` where Py2 was `//`, or forgot to wrap a view in list()), fix that
  specifically.
- Return ONLY the corrected Python 3 source. No fences, no commentary.
- Output must parse as valid Python 3.

This is repair iteration {iteration}. You have a limited budget; produce a
better attempt than last time or your fix will be rejected.
"""


def build_repair_prompt(
    source_py2: str,
    findings: List[Finding],
    prior_code: str,
    recent_tracebacks: List[str],
    iteration: int,
) -> str:
    tb_block = "\n\n---\n\n".join(recent_tracebacks) if recent_tracebacks else "(no traceback captured)"
    return REPAIR_TEMPLATE.format(
        prior_code=prior_code.rstrip() + "\n",
        tracebacks_block=tb_block,
        n_tracebacks=len(recent_tracebacks),
        findings_block=_render_findings_block(findings),
        iteration=iteration,
    )


# --- corrective retry on unparseable output ---------------------------------

CORRECTIVE_RETRY_TEMPLATE = """Your previous reply was not valid Python 3 source.
ast.parse(...) raised:

  {parse_error}

Return the migrated code AGAIN, fixing the parse error. Output ONLY the source -
no fences, no commentary, no explanation. Just valid Python 3.
"""


def build_corrective_retry_prompt(parse_error: str) -> str:
    return CORRECTIVE_RETRY_TEMPLATE.format(parse_error=parse_error)
