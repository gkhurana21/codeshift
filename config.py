"""CodeShift non-secret configuration.

Secrets (Anthropic API key, etc.) live in the environment / .env.
Anything in here is safe to commit.
"""

from __future__ import annotations

import logging
from pathlib import Path

# --- Paths --------------------------------------------------------------------

PROJECT_ROOT: Path = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR: Path = PROJECT_ROOT / "out"

# --- Model --------------------------------------------------------------------

# Project standard for the full Phase 3 benchmark run. The 4.6 generation uses
# the dateless ID as the canonical *pinned* snapshot (per Anthropic docs), so
# this is both readable and reproducible.
MODEL_NAME: str = "claude-sonnet-4-6"

# Env-var override (used for one-off demo runs without editing this file).
# `resolve_model_name(cli_value)` returns: cli_value | CODESHIFT_MODEL | MODEL_NAME.
MODEL_OVERRIDE_ENV: str = "CODESHIFT_MODEL"


def resolve_model_name(cli_value: str | None = None) -> str:
    """Pick the model identifier: CLI flag > env var > config default."""
    import os
    if cli_value:
        return cli_value
    return os.environ.get(MODEL_OVERRIDE_ENV) or MODEL_NAME


# --- Gemini (second backend) -------------------------------------------------
#
# NOT the global default. The project standard remains MODEL_NAME above
# (Anthropic, paid). GEMINI_MODEL_NAME is a convenience constant for the
# free-tier development path: pass `--model gemini-2.5-flash` (or set
# CODESHIFT_MODEL=gemini-2.5-flash) to use Gemini.
#
# Choice rationale: `gemini-2.5-flash` is on the Gemini API free tier (per
# Google's April 2026 policy: only Flash / Flash-Lite remain free; Pro is
# paid-only). Stable since 2025-06-17, retirement no earlier than 2026-10-16,
# 1M-token context. If you want a smarter free model, `gemini-3.5-flash`
# (released 2026-05-19) is the newer near-Pro-quality alternative.
GEMINI_MODEL_NAME: str = "gemini-2.5-flash"

# --- Agent loop ---------------------------------------------------------------

MAX_REPAIR_ITERATIONS: int = 5

# Hard budget caps so a runaway loop can't burn the API key.
MAX_TOKENS_PER_RUN: int = 200_000
MAX_TRACEBACKS_IN_REPAIR_PROMPT: int = 2

# --- Analyzer -----------------------------------------------------------------

# parso target grammar for Py2 input.
PY2_GRAMMAR_VERSION: str = "2.7"

# Severity vocabulary - kept small on purpose.
SEVERITY_INFO: str = "info"
SEVERITY_WARNING: str = "warning"
SEVERITY_ERROR: str = "error"

# --- Sandbox (used in Phase 3) -----------------------------------------------

DOCKER_PY2_IMAGE: str = "python:2.7-slim"
DOCKER_PY3_IMAGE: str = "python:3.11-slim"
SANDBOX_WALLCLOCK_SECONDS: int = 60

# --- Logging ------------------------------------------------------------------

LOG_LEVEL: int = logging.INFO
LOG_FORMAT: str = "%(asctime)s %(levelname)s %(name)s | %(message)s"


def configure_logging(level: int | None = None) -> None:
    """Idempotent logging setup. Greppable single-line format."""
    logging.basicConfig(
        level=level if level is not None else LOG_LEVEL,
        format=LOG_FORMAT,
    )
