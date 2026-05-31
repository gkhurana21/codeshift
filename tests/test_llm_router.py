"""Smoke tests for the provider router (`agent.llm.build_llm_client`).

These verify the single-source-of-truth backend selection logic WITHOUT
making any real API calls. Both `ChatAnthropic` and `ChatGoogleGenerativeAI`
are patched out so the test exercises:

  - prefix dispatch (claude-* -> AnthropicClient, gemini-* -> GeminiClient)
  - error path for unsupported prefixes (must list what IS supported)
  - that env-var-resolved model strings also dispatch correctly
  - that the API key for the *chosen* backend is the one that's required
    (an Anthropic key shouldn't satisfy a Gemini request and vice-versa)

We use `monkeypatch.setattr` on the lazy imports inside each client's
__init__, so no real langchain HTTP client is ever built.
"""

from __future__ import annotations

import pytest

from agent import llm as llm_mod
from agent.llm import AnthropicClient, GeminiClient, build_llm_client


# --- Fixtures: mock out the real chat-model classes -------------------------


class _FakeChatAnthropic:
    """Stand-in for langchain_anthropic.ChatAnthropic. Records init kwargs."""

    last_kwargs: dict | None = None

    def __init__(self, **kwargs):
        type(self).last_kwargs = kwargs


class _FakeChatGoogle:
    """Stand-in for langchain_google_genai.ChatGoogleGenerativeAI."""

    last_kwargs: dict | None = None

    def __init__(self, **kwargs):
        type(self).last_kwargs = kwargs


@pytest.fixture
def patched_backends(monkeypatch):
    """Patch both real SDK chat classes and provide both API keys.

    `AnthropicClient` and `GeminiClient` import their chat class lazily
    inside __init__, so we patch the module attribute that gets resolved at
    that point. We also neutralise `load_dotenv` inside `agent.llm` so the
    test never silently re-loads a developer's local `.env` and undoes a
    `monkeypatch.delenv(...)` we set up to prove the missing-key error path.
    """
    import langchain_anthropic
    import langchain_google_genai

    monkeypatch.setattr(langchain_anthropic, "ChatAnthropic", _FakeChatAnthropic)
    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", _FakeChatGoogle)
    monkeypatch.setattr(llm_mod, "load_dotenv", lambda *a, **kw: False)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    # Reset CODESHIFT_MODEL between tests to avoid cross-pollution.
    monkeypatch.delenv("CODESHIFT_MODEL", raising=False)

    _FakeChatAnthropic.last_kwargs = None
    _FakeChatGoogle.last_kwargs = None


# --- Router dispatch tests --------------------------------------------------


def test_router_dispatches_claude_prefix_to_anthropic(patched_backends):
    client = build_llm_client("claude-sonnet-4-6")
    assert isinstance(client, AnthropicClient)
    assert client.model == "claude-sonnet-4-6"
    # Confirm the mocked chat class actually got the resolved model.
    assert _FakeChatAnthropic.last_kwargs is not None
    assert _FakeChatAnthropic.last_kwargs["model"] == "claude-sonnet-4-6"


def test_router_dispatches_gemini_prefix_to_gemini(patched_backends):
    client = build_llm_client("gemini-2.5-flash")
    assert isinstance(client, GeminiClient)
    assert client.model == "gemini-2.5-flash"
    assert _FakeChatGoogle.last_kwargs is not None
    assert _FakeChatGoogle.last_kwargs["model"] == "gemini-2.5-flash"


def test_router_uses_config_default_when_no_model_arg(patched_backends):
    # MODEL_NAME defaults to claude-sonnet-4-6, so passing nothing routes there.
    client = build_llm_client()
    assert isinstance(client, AnthropicClient)


def test_router_respects_env_override_for_gemini(monkeypatch, patched_backends):
    monkeypatch.setenv("CODESHIFT_MODEL", "gemini-2.5-flash-lite")
    client = build_llm_client()
    assert isinstance(client, GeminiClient)
    assert client.model == "gemini-2.5-flash-lite"


def test_router_raises_clear_error_for_unsupported_prefix(patched_backends):
    with pytest.raises(ValueError) as excinfo:
        build_llm_client("gpt-4")
    msg = str(excinfo.value)
    # The error MUST list what IS supported so users can self-correct.
    assert "gpt-4" in msg
    assert "claude-" in msg
    assert "gemini-" in msg


def test_router_raises_clear_error_for_empty_or_garbage(patched_backends):
    with pytest.raises(ValueError):
        build_llm_client("llama-3")


# --- Auth: each backend requires its OWN key -------------------------------


def test_gemini_requires_gemini_api_key_not_anthropic(monkeypatch, patched_backends):
    # Only ANTHROPIC_API_KEY is set, GEMINI_API_KEY is not -> Gemini path errors.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as excinfo:
        build_llm_client("gemini-2.5-flash")
    assert "GEMINI_API_KEY" in str(excinfo.value)


def test_anthropic_requires_anthropic_api_key_not_gemini(monkeypatch, patched_backends):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as excinfo:
        build_llm_client("claude-sonnet-4-6")
    assert "ANTHROPIC_API_KEY" in str(excinfo.value)


# --- Token accounting parity ------------------------------------------------


def test_extract_usage_handles_both_backends_identically():
    """The shared `_extract_usage` reads the langchain-standard usage_metadata
    dict, which both Anthropic and Google clients populate the same way."""

    class _Msg:
        usage_metadata = {"input_tokens": 12, "output_tokens": 34, "total_tokens": 46}

    usage = llm_mod._extract_usage(_Msg())
    assert usage.input == 12
    assert usage.output == 34
    assert usage.total == 46


def test_fallback_token_estimate_is_nonzero_for_nonempty_text():
    # When a future SDK strips usage_metadata, the budget guard must NOT
    # silently become a no-op. The fallback always returns >=1 for non-empty.
    assert llm_mod._estimate_tokens_fallback("") == 0
    assert llm_mod._estimate_tokens_fallback("abcd") >= 1
    # ~4 chars/token, rounding up.
    assert llm_mod._estimate_tokens_fallback("a" * 40) >= 10
