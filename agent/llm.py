"""LLM client wrappers.

Three implementations behind a tiny common interface:
  * `AnthropicClient` - wraps langchain_anthropic.ChatAnthropic for real calls.
  * `GeminiClient`    - wraps langchain_google_genai.ChatGoogleGenerativeAI.
  * `FakeChatModel`   - scripted responses, used by tests and demos that need
    to exercise the repair-loop control flow without spending tokens.

Provider selection is centralized in `build_llm_client()` (single source of
truth): after `resolve_model_name`, dispatch on model-string prefix.

The interface (`LLMClient.invoke`) returns `LLMResponse` with both the raw
content and `TokenUsage`, so the loop can enforce the per-run token budget.
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Protocol

from dotenv import load_dotenv

from agent.schemas import TokenUsage
from config import resolve_model_name

log = logging.getLogger("codeshift.llm")

# Supported model-string prefixes -> backend. Used in error messages too.
_SUPPORTED_PREFIXES = ("claude-", "gemini-")


class QuotaExhaustedError(RuntimeError):
    """Raised when the LLM provider returns a quota/rate-limit error (HTTP 429).

    This is a sentinel that the benchmark runner propagates to the top level
    so the run halts cleanly rather than burning the remaining quota on retries.
    """


@dataclass
class LLMResponse:
    content: str
    usage: TokenUsage = field(default_factory=TokenUsage)


class LLMClient(Protocol):
    def invoke(self, system: str, user: str) -> LLMResponse: ...


# --- Real Anthropic client ---------------------------------------------------

class AnthropicClient:
    """Production client backed by langchain_anthropic.ChatAnthropic.

    Model selection precedence (handled by config.resolve_model_name):
        explicit `model=` arg  >  CODESHIFT_MODEL env var  >  config.MODEL_NAME

    The API key is read from ANTHROPIC_API_KEY (via .env if present) and is
    NEVER logged, printed, or echoed anywhere.
    """

    def __init__(self, model: str | None = None, temperature: float = 0.0, max_tokens: int = 4096):
        load_dotenv(override=True)  # override=True so .env wins over an empty shell export
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Put it in .env or export it. "
                "Never hardcode keys in source."
            )
        resolved = resolve_model_name(model)
        # Imported lazily so the rest of the codebase (and FakeChatModel-based
        # tests) doesn't pay the langchain import cost when not needed.
        from langchain_anthropic import ChatAnthropic
        self._chat = ChatAnthropic(
            model=resolved,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            max_retries=0,  # fail-fast on 429 — benchmark runner handles halting
        )
        self.model = resolved
        # Log the chosen model. We deliberately do NOT log the api_key.
        log.info("AnthropicClient initialised model=%s temperature=%s max_tokens=%d",
                 self.model, temperature, max_tokens)

    def invoke(self, system: str, user: str) -> LLMResponse:
        from langchain_core.messages import HumanMessage, SystemMessage
        log.info("llm invoke model=%s sys_chars=%d user_chars=%d", self.model, len(system), len(user))
        try:
            result = self._chat.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        except Exception as exc:
            # Anthropic raises anthropic.RateLimitError on HTTP 429.
            # Catch it here (via the exception name to avoid a hard import at
            # module level) and convert to our provider-neutral sentinel.
            if type(exc).__name__ == "RateLimitError" or "rate" in str(exc).lower() or "429" in str(exc):
                log.warning("quota guard triggered exc_type=%s repr=%r", type(exc).__qualname__, repr(exc)[:200])
                raise QuotaExhaustedError(
                    f"Anthropic quota/rate-limit exceeded: {exc}"
                ) from exc
            raise
        content = result.content if isinstance(result.content, str) else str(result.content)
        usage = _extract_usage(result)
        log.info("llm response tokens in=%d out=%d total=%d chars=%d",
                 usage.input, usage.output, usage.total, len(content))
        return LLMResponse(content=content, usage=usage)


def _extract_usage(ai_message) -> TokenUsage:
    """Pull token counts out of an AIMessage.usage_metadata, defensively."""
    meta = getattr(ai_message, "usage_metadata", None) or {}
    return TokenUsage(
        input=int(meta.get("input_tokens", 0) or 0),
        output=int(meta.get("output_tokens", 0) or 0),
    )


def _estimate_tokens_fallback(text: str) -> int:
    """Conservative char-based token estimate when the SDK omits usage_metadata.

    Clearly labeled fallback only - NOT authoritative billing. Uses ~4 chars/token
    (common rough heuristic) rounded up so budget guards stay conservative.
    """
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def _usage_from_message(
    ai_message,
    *,
    system: str,
    user: str,
    content: str,
    backend: str,
) -> TokenUsage:
    """Prefer SDK usage_metadata; fall back to estimate if both counts are zero."""
    usage = _extract_usage(ai_message)
    if usage.input > 0 or usage.output > 0:
        return usage
    if not (system or user or content):
        return usage
    log.warning(
        "token accounting: %s SDK returned no usage_metadata; "
        "using fallback char estimate (~4 chars/token)",
        backend,
    )
    return TokenUsage(
        input=_estimate_tokens_fallback(system + user),
        output=_estimate_tokens_fallback(content),
    )


# --- Real Gemini client ------------------------------------------------------

class GeminiClient:
    """Production client backed by langchain_google_genai.ChatGoogleGenerativeAI.

    The API key is read from GEMINI_API_KEY (via .env if present) and is
    NEVER logged, printed, or echoed anywhere.
    """

    def __init__(self, model: str | None = None, temperature: float = 0.0, max_tokens: int = 4096):
        load_dotenv(override=True)  # override=True so .env wins over an empty shell export
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Put it in .env or export it. "
                "Never hardcode keys in source."
            )
        resolved = resolve_model_name(model)
        from langchain_google_genai import ChatGoogleGenerativeAI
        self._chat = ChatGoogleGenerativeAI(
            model=resolved,
            temperature=temperature,
            max_output_tokens=max_tokens,
            google_api_key=api_key,
            max_retries=0,  # fail-fast on 429 — benchmark runner handles halting
        )
        self.model = resolved
        log.info("GeminiClient initialised model=%s temperature=%s max_tokens=%d",
                 self.model, temperature, max_tokens)

    def invoke(self, system: str, user: str) -> LLMResponse:
        from langchain_core.messages import HumanMessage, SystemMessage
        log.info("llm invoke model=%s sys_chars=%d user_chars=%d", self.model, len(system), len(user))
        try:
            result = self._chat.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        except Exception as exc:
            # google.api_core.exceptions.ResourceExhausted is raised for HTTP 429.
            # With max_retries=0 it propagates immediately (no langchain sleep loop).
            if type(exc).__name__ == "ResourceExhausted" or "quota" in str(exc).lower() or "429" in str(exc):
                log.warning("quota guard triggered exc_type=%s repr=%r", type(exc).__qualname__, repr(exc)[:200])
                raise QuotaExhaustedError(
                    f"Gemini quota/rate-limit exceeded: {exc}"
                ) from exc
            raise
        content = result.content if isinstance(result.content, str) else str(result.content)
        usage = _usage_from_message(
            result, system=system, user=user, content=content, backend="Gemini",
        )
        log.info("llm response tokens in=%d out=%d total=%d chars=%d",
                 usage.input, usage.output, usage.total, len(content))
        return LLMResponse(content=content, usage=usage)


# --- Provider router (single source of truth) ---------------------------------

def build_llm_client(
    model: str | None = None,
    *,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> LLMClient:
    """Resolve the model string, then dispatch to the matching backend client.

    Precedence for the model string: explicit `model` arg > $CODESHIFT_MODEL >
    config.MODEL_NAME (see config.resolve_model_name).

    Prefix dispatch:
      * ``claude-*`` -> AnthropicClient (requires ANTHROPIC_API_KEY)
      * ``gemini-*`` -> GeminiClient     (requires GEMINI_API_KEY)

    Raises ValueError for any other prefix, listing what IS supported.
    """
    resolved = resolve_model_name(model)
    if resolved.startswith("claude-"):
        return AnthropicClient(model=resolved, temperature=temperature, max_tokens=max_tokens)
    if resolved.startswith("gemini-"):
        return GeminiClient(model=resolved, temperature=temperature, max_tokens=max_tokens)
    raise ValueError(
        f"Unsupported model {resolved!r}. "
        f"Supported prefixes: {_SUPPORTED_PREFIXES[0]!r} (Anthropic) and "
        f"{_SUPPORTED_PREFIXES[1]!r} (Google Gemini). "
        f"Example: --model claude-sonnet-4-6 or --model gemini-2.5-flash"
    )


# --- Fake model for deterministic loop tests --------------------------------

class FakeChatModel:
    """Scripted LLM for tests and demos that exercise loop control flow.

    Pass either a list of responses (consumed in order) or a callable that
    receives (system, user, call_index) and returns a string. After scripted
    responses are exhausted, raises RuntimeError unless `loop=True` (then it
    re-emits the last response forever - useful for oscillation tests).
    """

    def __init__(
        self,
        responses: Optional[List[str]] = None,
        responder: Optional[Callable[[str, str, int], str]] = None,
        loop: bool = False,
        tokens_per_call: int = 100,
    ):
        if (responses is None) == (responder is None):
            raise ValueError("Provide exactly one of `responses` or `responder`.")
        self._responses = list(responses) if responses else None
        self._responder = responder
        self._loop = loop
        self._tokens_per_call = tokens_per_call
        self._call_index = 0
        self.calls: List[tuple[str, str]] = []

    def invoke(self, system: str, user: str) -> LLMResponse:
        self.calls.append((system, user))
        if self._responder is not None:
            content = self._responder(system, user, self._call_index)
        else:
            assert self._responses is not None
            if self._call_index < len(self._responses):
                content = self._responses[self._call_index]
            elif self._loop:
                content = self._responses[-1]
            else:
                raise RuntimeError(
                    f"FakeChatModel exhausted: got call #{self._call_index + 1} "
                    f"but only {len(self._responses)} scripted responses (loop=False)."
                )
        self._call_index += 1
        return LLMResponse(
            content=content,
            usage=TokenUsage(input=self._tokens_per_call // 2, output=self._tokens_per_call // 2),
        )
