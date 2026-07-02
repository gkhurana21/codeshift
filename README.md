# CodeShift

[![CI](https://github.com/gkhurana21/codeshift/actions/workflows/test.yml/badge.svg)](https://github.com/gkhurana21/codeshift/actions/workflows/test.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**An LLM agent that migrates Python 2 code to Python 3 and verifies behavioral correctness — not just syntax — against a 41-case behavioral oracle benchmark. 95.1% pass rate, byte-identical across two LLM providers.**

A *behavioral oracle* is a hand-authored test file that encodes what the Py2 program actually returned (values, exception types, side effects), so a migration only passes if it preserves runtime behavior — not merely if it parses under Python 3.

Unlike `2to3`-style tools that rewrite syntax and stop, CodeShift runs the migrated code against these oracles, catches semantic regressions (silent integer-division changes, `str`/`bytes` boundary breaks, exception-context leaks), and feeds failures back into a repair loop until the migration passes or budgets are exhausted.

## How the agent loop works

```
analyze ──> transform ──> write to sandbox ──> run oracle tests
                ^                                    │
                │            pass ── done            │
                └── repair prompt (last 1-2 ── fail ─┘
                    tracebacks only)
```

1. **Analyze.** A [parso](https://github.com/davidhalter/parso)-based static analyzer parses the source with the Py2.7 grammar (parso is error-tolerant, so files with Py2-only syntax still yield a tree) and emits findings — mechanical rewrites tagged separately from semantic-risk constructs.
2. **Transform.** The LLM receives the source plus the analyzer findings and produces a Py3 candidate.
3. **Verify.** The candidate runs against the case's behavioral oracle in a sandboxed subprocess (process-group kill on timeout, `RLIMIT_AS` memory cap for benchmark runs).
4. **Repair.** On failure, the agent gets a repair prompt carrying only the most recent 1–2 tracebacks and tries again.

Guards on the loop: identical-code **oscillation detection**, **best-attempt tracking** (most tests passed wins, ties to earliest), and per-run **token and iteration budgets**. Every iteration logs a greppable `iter=N case=NAME passed=P failed=F action=...` line.

**LLM backends:** `claude-*` → Anthropic API, `gemini-*` → Google Gemini, dispatched by model-name prefix via `build_llm_client()`.

## Benchmark results

41 hand-authored cases, each targeting one distinct semantic trap, grouped into pre-registered difficulty bands. The failure categories were written down **before** the corpus run, so the two failures land in a predicted class rather than being explained after the fact.

| Band | Cases | Gemini 2.5 Flash | Claude Sonnet 4.6 |
|---|---:|---:|---:|
| Clean / mechanical | 21 | 21/21 | 21/21 |
| Group A — Undecidable from source | 12 | 12/12 | 12/12 |
| Group B — Decidable, high-miss-risk | 6 | 4/6 | 4/6 |
| Multi-trap | 2 | 2/2 | 2/2 |
| **Overall** | **41** | **39/41 = 95.1%** | **39/41 = 95.1%** |
| Total tokens | | 122,748 | 67,527 |

Two models from different providers, a capability tier apart, produce **byte-identical pass/fail on all 41 cases** — including the same two failures: both agents convert `except E, e:` correctly but fail to add `raise ... from None`, leaving the caught exception attached as `__context__`. A shared gap across providers suggests it may be a property of LLM exception-semantic reasoning, though n=2 models is suggestive, not conclusive. Secondary finding: Claude reaches the same score at roughly 55% of Gemini's token cost.

Full methodology, pre-registered failure categories, known limitations, and per-case results: [docs/METHODOLOGY.md](docs/METHODOLOGY.md). Corpus design and oracle integrity rules: [benchmark/README.md](benchmark/README.md).

## Quickstart

```bash
git clone https://github.com/gkhurana21/codeshift.git
cd codeshift
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY or GEMINI_API_KEY (Gemini free tier works)
```

Migrate a single file:

```bash
python -m agent.migrate samples/gnarly_py2.py
```

Run the full 41-case benchmark:

```bash
CODESHIFT_MODEL=gemini-2.5-flash python -m benchmark.run_all   # free tier
python -m benchmark.run_all --model claude-sonnet-4-6          # canonical run
```

Run the unit test suite (no API keys needed):

```bash
pytest tests/
```

## Architecture

```
analyzer/      parso-based static analyzer — detects Py2 constructs, tags
               semantic-risk items distinctly from mechanical rewrites
agent/         LangChain repair loop — transform, test, repair; oscillation
               detection, best-attempt tracking, token/iteration budgets
sandbox/       Subprocess runners: LocalSubprocessSandbox (dev) and
               HardenedSubprocessSandbox (benchmark: process-group kill,
               RLIMIT_AS cap, .pyc-staleness guards)
benchmark/     41-case corpus + runner. Each case: source_py2.py +
               test_behavior.py (the behavioral oracle)
docs/          Full methodology, pre-registered categories, results
```

## License

MIT — see [LICENSE](LICENSE).
