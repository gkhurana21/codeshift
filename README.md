# CodeShift

[![CI](https://github.com/gkhurana21/codeshift/actions/workflows/test.yml/badge.svg)](https://github.com/gkhurana21/codeshift/actions/workflows/test.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**CodeShift migrates Python 2 codebases to Python 3 using an LLM agent that
verifies behavioral correctness — not just syntax — through a hand-authored
oracle test suite.**

Unlike `2to3`-style tools that rewrite syntax and stop, CodeShift runs the
migrated code against behavioral tests that encode what the Py2 program
*actually did*, catches semantic regressions, and feeds failures back into a
repair loop until the migration passes or the agent's limits are reached.

### Key benchmark finding

> Gemini 2.5 Flash and Claude Sonnet 4.6 — different providers, a capability
> tier apart — produce **byte-identical pass/fail on all 41 benchmark cases**
> (39/41 = 95.1%). Both failures are in the same pre-registered category: a
> systematic inability to add `raise ... from None` during exception migration.
> Agents correctly convert `except E, e:` → `except E as e:` but do not
> suppress `__context__`, leaving the caught exception attached to the re-raise.
> That this gap is shared across both models suggests it may be a property of
> LLM exception-semantic reasoning — though n=2, so the claim is suggestive,
> not conclusive.

| Band | Cases | Gemini 2.5 Flash | Claude Sonnet 4.6 |
|---|---|---|---|
| Clean / mechanical | 21 | 21/21 ✓ | 21/21 ✓ |
| Group A — Undecidable from source | 12 | 12/12 ✓ | 12/12 ✓ |
| Group B — Decidable, high-miss-risk | 6 | 4/6 | 4/6 |
| Multi-trap | 2 | 2/2 ✓ | 2/2 ✓ |
| **Overall** | **41** | **39/41 = 95.1%** | **39/41 = 95.1%** |
| Total tokens | | 122,748 | 67,527 |

---

## Quickstart

```bash
git clone https://github.com/gkhurana21/codeshift.git
cd codeshift
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your API key — Gemini free tier works
```

Migrate a single file:
```bash
python -m agent.migrate samples/gnarly_py2.py
```

Run the full 41-case benchmark (one run, results are locked — do not re-roll):
```bash
# Gemini (free tier, good for iteration):
CODESHIFT_MODEL=gemini-2.5-flash python -m benchmark.run_all

# Claude (paid, canonical measurement):
python -m benchmark.run_all --model claude-sonnet-4-6
```

Run the unit test suite (no API keys needed):
```bash
pytest tests/
```

**Model support:** `claude-*` → Anthropic API (`ANTHROPIC_API_KEY`),
`gemini-*` → Google Gemini (`GEMINI_API_KEY`). Model selection: explicit
`--model` flag > `$CODESHIFT_MODEL` env var > `config.MODEL_NAME` default.

---

## Architecture

```
analyzer/      parso 0.7.1-based static analyzer — detects Py2 constructs,
               tags semantic-risk items distinctly from mechanical rewrites.

agent/         LangChain repair loop — transforms source, runs tests, repairs
               on failure. Guards: oscillation detection, best-attempt tracking,
               token/iteration budget, corrective retry on parse failures.

sandbox/       Subprocess runners for the test-feedback loop.
               LocalSubprocessSandbox  — dev/agent use.
               HardenedSubprocessSandbox — benchmark use (process-group kill on
               timeout, RLIMIT_AS memory cap, .pyc-staleness guards).

benchmark/     Hand-authored corpus + runner. Each case: source_py2.py +
               test_behavior.py (behavioral oracle). Runner: benchmark/run_all.py.
```

LLM backends: `claude-*` → Anthropic, `gemini-*` → Google Gemini. Dispatch via
`build_llm_client(model)`. The canonical benchmark model is `claude-sonnet-4-6`;
`gemini-2.5-flash` is used for free iteration runs.

---

## Benchmark Methodology

### What "behavioral oracle" means

Each benchmark case is hand-authored with a test file (`test_behavior.py`) that
encodes the **correct Py3 result based on documented Py2 semantics**, not the
result a naïve Py3 transform would produce.

Example: a Py2 function `average([1, 2])` that relied on integer division returns
`1` (floor). The oracle asserts `average([1, 2]) == 1`. A migration that replaces
`/` with `/` (unchanged) produces `1.5` and fails the oracle. A correct migration
uses `//` and passes.

No Python 2.7 interpreter is required. The oracle encodes what Py2 *would have*
returned, verified by the author against the language specification. The pass rate
is defensible because every oracle has a documented, hand-verified behavioral
claim.

### Oracle integrity rules

- Every assertion in every oracle must **fail on the unmigrated Py2 source** when
  run under Python 3 (verified by a bite check before each corpus run).
- No assertion may pass on naïvely-migrated code (syntax-only 2to3-style fix) if
  the trap is a semantic one. Exact-division inputs in integer-division oracles,
  and source functions already Py3-safe in dict-view oracles, are forbidden for
  this reason.
- Exception: `pytest.raises` guards for error paths that fire identically in both
  Py2 and Py3 (e.g., `ValueError` on an empty list) are permitted since they pin
  correctness, not the trap.

### Corpus structure

```
benchmark/cases/{name}/
    source_py2.py     — Py2 source to migrate (parseable by parso 0.7.1 as py2.7)
    test_behavior.py  — behavioral oracle
```

Each case targets **one semantic trap**; no two cases share a trap.

### How to run

```bash
# Free iteration (Gemini):
CODESHIFT_MODEL=gemini-2.5-flash .venv/bin/python -m benchmark.run_all

# Reportable number (Claude — run once, after corpus is stable):
ANTHROPIC_API_KEY=... .venv/bin/python -m benchmark.run_all --model claude-sonnet-4-6

# Subset:
.venv/bin/python -m benchmark.run_all --cases integer_division,str_bytes
```

---

## Pre-Registered Failure Categories

**Written before the full ~40-case corpus run and before any Claude results.**
These are categories where a correct-by-construction migration may be impossible
or where the agent is expected to struggle. Each failure in the full-corpus run
will be mapped to one of these categories, or flagged as surprising.

The categories are divided into two distinct claims:

- **Group A — Undecidable from source:** No correct-by-construction transform
  exists. Any choice the agent makes may be wrong for some callers or some intent.
  A pass in this group is the oracle pinning one defensible interpretation, not the
  agent solving a solved problem.

- **Group B — Decidable but high-miss-risk:** A correct Py3 transform exists and
  is derivable from the source alone, but requires the agent to recognise a
  specific idiom or perform a coordinated multi-site rewrite. The agent may fail
  even though a correct answer is available.

---

### Group A — Undecidable from source

*No correct-by-construction transform exists. The source alone does not contain
enough information to determine the single correct Py3 equivalent.*

---

#### Category F1 — `str`/`bytes` intent genuinely ambiguous at the call boundary

**What it is.** In Py2, `str` and `bytes` are the same type. A function that
accepts a `str` argument could be receiving bytes (raw data) or text (ASCII
happening to fit in bytes), and the source gives no indication which. The correct
Py3 signature depends on what callers pass at runtime.

**Why the transform is undecidable.** Without runtime information, the agent
cannot determine whether to type the parameter as `str` or `bytes`. Either choice
may be wrong for some callers. Code that worked in Py2 by accident (both types
were one type) is genuinely ambiguous in Py3. The oracle can pin *one*
interpretation, but a real codebase may have both call sites.

**Example shape.** `def process(data): return data + '\n'` — if callers pass
raw bytes, the Py3 migration needs `b'\n'`; if callers pass text, it needs `'\n'`.
The source alone cannot resolve this.

**Expected prevalence in corpus.** Medium. Hand-authored cases avoid this by
construction (oracles pass `b"..."` literals), but cases that try to handle both
types in one function, or that read from files opened in ambiguous mode, will hit
this.

---

#### Category F2 — Integer division where float was the *intended* behavior

**What it is.** Py2's `/` on integers silently floor-divides. Some Py2 code
*intended* float division and got away with integer inputs that happened to divide
evenly, or the author didn't notice the truncation. The "correct" Py3 migration
should use `//` to preserve the Py2 *observed* behavior — but if the author
intended `/` to produce a float, using `//` preserves the bug, not the intent.

**Why the transform is undecidable.** The agent has no access to the programmer's
intent, only to the source. The static analyzer flags `/` on integer operands as a
semantic risk, but cannot determine which semantics the programmer wanted. Our
oracle encodes the Py2-observed behavior (floor), so the agent "passes" by
preserving the bug. In a real codebase, both fixes (`//` and `/`) are defensible;
the oracle makes only one right.

**Expected prevalence in corpus.** Low for hand-authored cases (we deliberately
encode Py2 floor semantics in oracles). Higher if we add cases where the function
name or context implies ratio/fraction intent (e.g., `def ratio(a, b): return a / b`).

---

#### Category F7 — `unicode_literals` future import interaction

**What it is.** Py2 code with `from __future__ import unicode_literals` makes all
bare string literals unicode. A migration that also adds `unicode → str`
substitutions to such a file may double-encode: the literals are already unicode,
and if the agent additionally wraps them in `str()` calls or changes their type
assumptions, string operations may fail.

**Why the transform is undecidable.** The agent must detect the future import and
suppress `str` / `unicode` coercion changes that are redundant or harmful under
it. Without recognising this interaction, the migrated code may pass analysis but
encode strings incorrectly at runtime for non-ASCII content. Whether to suppress
these coercions is not derivable from syntax alone — it depends on whether the
non-ASCII handling throughout the file was written assuming text or bytes.

**Expected prevalence in corpus.** Low unless we explicitly include `__future__`
cases. Planned for scaled corpus.

---

### Group B — Decidable but high-miss-risk for the agent

*A correct Py3 transform exists and is derivable from the source alone. The agent
may fail because the transform requires recognising a specific idiom or
coordinating changes across multiple sites simultaneously.*

---

#### Category F4 — `map(None, ...)` / `zip`-pad idiom

**What it is.** Py2's `map(None, seq1, seq2)` with a `None` function zips two
sequences and pads the shorter one with `None` (unlike `zip`, which stops at the
shorter). Py3's `map` does not accept `None` as the function for this purpose, and
there is no direct single-expression replacement (`itertools.zip_longest` is the
equivalent).

**Why the agent may miss it.** The agent must recognise this specific idiom. If it
treats `map(None, ...)` as a plain `map()` call and either drops the argument or
converts to `list(map(None, ...))`, the Py3 code raises `TypeError`. The analyzer
does not flag `map(None, ...)` as a distinct construct from `map(func, ...)`.
Unless the model recognises the idiom from training, it will fail — but the
correct transform (`itertools.zip_longest`) is unambiguous once the idiom is
identified.

**Expected prevalence in corpus.** Low but nonzero. A deliberate case targeting
this idiom is planned for the scaled corpus.

---

#### Category F5 — `__cmp__` / `cmp()` builtin removal

**What it is.** Py2 objects can define `__cmp__(self, other)` returning negative/
zero/positive. The `cmp()` builtin and `sorted(x, cmp=...)` form both rely on
this. In Py3, `__cmp__` is silently ignored (not an error), `cmp()` is removed,
and `sorted` does not accept a `cmp=` keyword.

**Why the agent may miss it.** The agent must (a) replace the `cmp()` call site,
(b) convert `__cmp__` to `__lt__`/`__gt__`/`__eq__`/etc., and (c) replace
`sorted(x, cmp=f)` with `sorted(x, key=functools.cmp_to_key(f))`. Any one of
these done alone while the others are left breaks the code. The three fixes are
interdependent, and the static analyzer only flags the call site, not the method
definition. A correct transform exists; the risk is partial application.

**Expected prevalence in corpus.** Low for simple cases; higher for object-sorting
code. Planned for scaled corpus.

---

#### Category F6 — Exception context on re-raise

**What it is.** In Py3, an exception raised inside an `except` block carries an
implicit `__context__` (the caught exception). Code that catches an exception,
raises a new one, and then inspects the raised exception's string representation
may see additional text (`"During handling of the above exception..."`) in Py3 that
was not present in Py2.

**Why the agent may miss it.** The syntax migration (`except E, e` → `except E as
e`) is mechanical and correct. But if the oracle asserts on the exact string of a
re-raised exception, the Py3 exception context changes the representation. The
correct Py3 fix is `raise X from None` to suppress `__context__` — this is
derivable from the source once the re-raise pattern is identified, but requires
the agent to recognise that the context chain will alter string output.

**Expected prevalence in corpus.** Low. Only affects oracles that assert on
exception message strings across a re-raise boundary.

---

### Corpus Construction Constraint — Dict ordering non-determinism

This is not a migration failure category. The migration for `d.keys()[0]` →
`list(d.keys())[0]` is unambiguously correct, and the agent is not expected to
fail on it. The constraint is an *oracle-authoring hazard*:

Py2 dict iteration order is arbitrary (CPython 2.7 uses hash order, which varies
between runs and Python builds). A test that asserts a specific first key from a
multi-element dict will be non-deterministic unless Py3.7+ insertion-order
guarantees happen to match what the test expects. The agent's migration is
correct; an oracle that asserts on ordering across multi-element dicts is fragile.

**Corpus rule.** Oracles that index into dict key/value lists must use
single-element dicts, or must assert on `sorted()` output. Multi-element dicts
with ordering-sensitive assertions are forbidden. This constraint is already
applied to the `dict_view_index` case and must be enforced for all new dict cases
in the scaled corpus.

---

## Known Limitations (recorded before full-corpus run)

### L1 — Static analyzer has no coverage of the `str`-as-bytes / `ord`·`chr` idiom

In the 7-case Gemini iteration run (`gemini-2.5-flash`, 2026-05-30), the
`str_bytes` case — which exercises `ord(c)` / `chr(n)` byte manipulation on Py2
`str` — produced **0 analyzer findings**. The static analyzer's semantic-risk
detection does not cover the pattern of iterating a `str` (Py2 bytes) and calling
`ord()`/`chr()` per character.

The agent nonetheless migrated this case correctly on the first iteration. It
succeeded from source context (the module docstring and per-function docstrings
explicitly described the Py2 bytes semantics) rather than from analyzer-driven
semantic flagging. The SEMANTIC RISK block in the prompt contributed nothing to
this case.

**Implication for the architecture.** The analyzer-→-prompt pipeline is not
providing signal for this class of idiom. On real-world Py2 code that uses
`ord()`/`chr()` byte manipulation without documenting the intent, the agent would
be reasoning without the analyzer's guidance. Whether it would still succeed is
unknown.

**Implication for the benchmark.** Hand-authored docstrings that explicitly
describe byte-level semantics may make the `str_bytes` case easier than a field
case would be. The 100% pass rate on this case is not fully representative of
real-world difficulty for this trap class. This is noted but not fixed before the
Claude run; the case remains in the corpus as-authored.

**Planned follow-up (post-Claude run).** Consider adding a `str_bytes` variant
with no documenting docstrings to measure how much the analyst gap costs.

---

### L2 — Corpus size (7 cases) is below the threshold for a defensible pass rate

The 7-case Gemini iteration run produced 100% (7/7). This number is not reported
as a headline metric. At 7 cases, the confidence interval on a pass rate is too
wide to be meaningful, and the cases are too few to expose tail failures.

The reportable number was produced from the 41-case scaled corpus using
`gemini-2.5-flash`, run once on 2026-05-30 after the corpus was fully locked
(41/41 bite-check, docstring audit clean). See the Results section below.

---

## Results

### Gemini iteration run (starter corpus) — 2026-05-28 (NOT the reportable number)

Model: `gemini-2.5-flash` · Cases: 7 · Corpus state: starter set only

```
 CASE                     STATUS   ITERS  TOKENS   ORACLE     TIME
 dict_iteration           PASS         1    1777      7/7     6.5s
 dict_view_index          PASS         1    1884      7/7     5.0s
 exception_syntax         PASS         1    1580      9/9     4.1s
 integer_division         PASS         1    1828      6/6     4.6s
 map_iterator             PASS         1    2176      7/7     7.2s
 str_bytes                PASS         1    3346      7/7    11.8s
 text_encoding            PASS         1    3538    12/12    11.7s

 TOTAL: 7 cases · 7 PASS · 0 FAIL · pass rate: 100.0%
 All 7 cases resolved on the initial transform; zero repair iterations used.
```

Notable: `str_bytes` passed despite 0 analyzer findings (see L1 above). Not
reported as a headline metric — 7 cases is too small for a defensible pass rate.

---

### Full-corpus measurement — 2026-05-30

Model: `gemini-2.5-flash` · Cases: 41 · Corpus state: locked (41/41 bite-check
green, docstring audit clean, pre-registered categories confirmed)

Run command:
```bash
CODESHIFT_MODEL=gemini-2.5-flash .venv/bin/python -m benchmark.run_all
```

Total tokens: 122,748 across 41 cases.

#### Per-band scorecard

| Band | Cases | Pass | Rate |
|------|------:|-----:|-----:|
| Clean / mechanical | 21 | 21 | **100.0%** |
| Group A — Undecidable from source | 12 | 12 | **100.0%** |
| Group B — Decidable, high-miss-risk | 6 | 4 | **66.7%** |
| Multi-trap | 2 | 2 | **100.0%** |
| **Aggregate** | **41** | **39** | **95.1%** |

The 95.1% blended number should be read through the per-band lens.
66.7% on Group B is the number that matters for agent capability;
it reflects a pre-registered difficulty class, not a surprise.

#### Per-case results

```
 CASE                      BAND     STATUS  ITERS   TOKENS  ORACLE
──────────────────────────────────────────────────────────────────
 apply_builtin             clean    PASS      1       855    6/6
 bandwidth_estimator       group_a  PASS      2     3,685    3/3
 basestring_isinstance     clean    PASS      1       887   10/10
 cmp_builtin               clean    PASS      1     2,497   11/11
 column_merger             group_b  PASS      1     2,242    7/7
 config_value_encoder      group_a  PASS      2     6,059    7/7
 csv_field_builder         group_a  PASS      2     4,243    6/6  †
 dict_iteration            clean    PASS      1     2,172    7/7
 dict_view_index           clean    PASS      1     1,904    7/7
 error_translator          group_b  FAIL      2    14,754    3/6  ✗ F6
 exception_syntax          clean    PASS      1     1,540    9/9
 exec_statement            clean    PASS      1       887    6/6
 frame_buffer              group_a  PASS      1     1,531    7/7
 has_key_method            clean    PASS      1     1,096    8/8
 http_body_processor       group_a  PASS      4     9,017    7/7  ‡
 integer_division          group_a  PASS      1     1,828    6/6
 iterator_next             clean    PASS      1       878    5/5
 itertools_izip_imap       clean    PASS      1     1,642    6/6
 legacy_io_handler         multi    PASS      1     1,291    5/5
 long_integer              clean    PASS      1     1,114    8/8
 map_iterator              clean    PASS      1     2,176    7/7
 metaclass_declaration     clean    PASS      1     1,235    5/5
 octal_literal             clean    PASS      1     1,290    8/8
 print_function            clean    PASS      1     1,033    5/5
 priority_task             group_b  PASS      1     2,966    6/6
 raise_comma_syntax        clean    PASS      1       874    7/7
 raw_input_call            clean    PASS      1       955    6/6
 reduce_builtin            clean    PASS      1       769    7/7
 report_builder            multi    PASS      2     3,754    6/6
 sliding_average           group_a  PASS      2     3,517    3/3
 str_bytes                 group_a  PASS      1     3,346    7/7
 string_module_attrs       clean    PASS      2     2,849    6/6
 success_rate              group_a  PASS      2     3,229    3/3
 text_encoding             group_a  PASS      1     3,538   12/12
 unicode_codec_pipeline    group_a  PASS      1     2,296    8/8
 unicode_template_renderer group_a  PASS      1     2,087    9/9
 validation_chain          group_b  FAIL      2    13,465    4/6  ✗ F6
 version_sort              group_b  PASS      1     3,946    7/7
 xrange_iteration          clean    PASS      1     1,228    7/7
 zip_exhaustion            clean    PASS      2     6,419    5/5
 zip_pad                   group_b  PASS      1     1,654    6/6
```

#### Failure analysis

Both failures are **pre-registered F6 (Group B — agent-limitation)**. Neither
is a surprise.

**`error_translator` — F6, OSCILLATION, 3/6 oracle**

The agent correctly converted all three `except KeyError/ValueError/
ZeroDivisionError, e:` clauses to `except E as e:`. It did not add `from None`
to any of the three re-raises. All three `__context__` assertions failed. The
repair loop reached the same 3/6 state at iter 2 as iter 1; iter 3 produced
a malformed parse followed by an oscillation match, halting early.

The correct fix — `raise AppError(...) from None` — is derivable from source
alone; the agent identified the syntax trap but not the implicit-context trap.
This is the expected F6 failure mode.

**`validation_chain` — F6, OSCILLATION, 4/6 oracle**

Same root cause: `except ValueError as e:` and `except (ValidationError,
ParseError) as e:` are syntactically correct, but neither re-raise uses
`from None`. Two tests that assert `.__context__ is None` fail. The repair
loop held at 4/6 across iters 1 and 2. At iter 3 the model produced code
with a syntax error (`SyntaxError: '(' was never closed`) — a real failure
of the repair loop's code-generation quality under repeated pressure. A
corrective retry was attempted and matched iter 2, triggering the oscillation
guard and halting the run. This case demonstrates both the F6 miss and a
genuine repair-loop degradation: the model generated invalid Python on its
third rewrite attempt.

#### Notes on notable passes

**`csv_field_builder` (†) — Group A / F1, coin-flip pass, do not count as F1 competence**

The Py2 source is pure `str` throughout (`SEP = ','`, `return str(value)`).
The oracle pins the bytes output path. The agent migrated to bytes
(`SEP = b','`, `str(value).encode('utf-8')`), which matched the oracle and
passed. A str-throughout migration would have been equally valid Py3 and
would have failed the oracle. This pass reflects a lucky alignment between
the agent's arbitrary choice and the oracle's arbitrary pin — not the agent
resolving genuine F1 ambiguity. **Group A's 100% pass rate does not
demonstrate competence on genuinely-undecidable cases.** It demonstrates
the agent can produce one defensible interpretation of an ambiguous source,
and that interpretation happened to match the oracle in all 12 group\_a cases.
The harder F1 question — whether the agent picks the *right* interpretation
for a real codebase — remains unanswered by this corpus.

**`http_body_processor` (‡) — Group A / F1, legitimate F1 success, 4 iterations**

Iteration trajectory: 0/7 → 3/7 → 5/7 → 7/7. The Py2 source uses bare
string literals for HTTP framing characters (`'\r\n'`, `'content-length:'`,
`'\n'`). Unlike `csv_field_builder`, the bytes interpretation is
unambiguous from domain context: HTTP header parsing and chunked body
decoding are always byte-stream operations. The agent correctly inferred
bytes intent from the function names and structure, committing to `b'\r\n'`,
`b'content-length:'`, etc. across all three functions. The 4-iteration cost
reflects genuine difficulty in simultaneously converting every literal and
accumulator — not a fundamentally undecidable choice.

---

### Claude Sonnet 4.6 — full-corpus measurement — 2026-05-30

Model: `claude-sonnet-4-6` · Cases: 41 · Corpus state: same locked corpus as
Gemini run (identical source, identical oracles, identical bite-check)

Run command:
```bash
.venv/bin/python -m benchmark.run_all --model claude-sonnet-4-6
```

Total tokens: 67,527 across 41 cases.

**Methodology note — llm.py mid-session modification.** `agent/llm.py` was
patched between the Gemini run and the Claude run to add `load_dotenv(override=True)`
in both `AnthropicClient` and `GeminiClient`, fixing a bug where an empty
`ANTHROPIC_API_KEY=''` pre-set in the shell environment blocked `.env` from
loading the real key. The Gemini run used the pre-fix version; the Claude run
used the post-fix version. The fix affects only API key loading at client
initialization — it has no effect on model behavior, prompts, sampling, or
the repair loop. Both runs produced clean output with zero API errors. Results
are valid; the implementation-state difference is noted for completeness.

#### Per-band scorecard

| Band | Cases | Pass | Rate |
|------|------:|-----:|-----:|
| Clean / mechanical | 21 | 21 | **100.0%** |
| Group A — Undecidable from source | 12 | 12 | **100.0%** |
| Group B — Decidable, high-miss-risk | 6 | 4 | **66.7%** |
| Multi-trap | 2 | 2 | **100.0%** |
| **Aggregate** | **41** | **39** | **95.1%** |

#### Per-case results

```
 CASE                       BAND     STATUS  ITERS   TOKENS  ORACLE
──────────────────────────────────────────────────────────────────
 apply_builtin              clean    PASS      1       637    6/6
 bandwidth_estimator        group_a  PASS      1       713    3/3
 basestring_isinstance      clean    PASS      1       760   10/10
 cmp_builtin                clean    PASS      1       969   11/11
 column_merger              group_b  PASS      1       596    7/7
 config_value_encoder       group_a  PASS      2     2,175    7/7
 csv_field_builder          group_a  PASS      2     1,606    6/6
 dict_iteration             clean    PASS      1     1,617    7/7
 dict_view_index            clean    PASS      1     1,291    7/7
 error_translator           group_b  FAIL      2     6,045    3/6  ✗ F6
 exception_syntax           clean    PASS      1     1,234    9/9
 exec_statement             clean    PASS      1       768    6/6
 frame_buffer               group_a  PASS      2     1,730    7/7
 has_key_method             clean    PASS      1       910    8/8
 http_body_processor        group_a  PASS      4     5,233    7/7
 integer_division           group_a  PASS      1     1,367    6/6
 iterator_next              clean    PASS      1       698    5/5
 itertools_izip_imap        clean    PASS      1       722    6/6
 legacy_io_handler          multi    PASS      1     1,035    5/5
 long_integer               clean    PASS      1       726    8/8
 map_iterator               clean    PASS      1     1,187    7/7
 metaclass_declaration      clean    PASS      1       681    5/5
 octal_literal              clean    PASS      1       979    8/8
 print_function             clean    PASS      1       773    5/5
 priority_task              group_b  PASS      1     1,017    6/6
 raise_comma_syntax         clean    PASS      1       716    7/7
 raw_input_call             clean    PASS      1       733    6/6
 reduce_builtin             clean    PASS      1       709    7/7
 report_builder             multi    PASS      2     2,593    6/6
 sliding_average            group_a  PASS      1       713    3/3
 str_bytes                  group_a  PASS      1     1,341    7/7
 string_module_attrs        clean    PASS      2     1,477    6/6
 success_rate               group_a  PASS      3     2,818    3/3
 text_encoding              group_a  PASS      1     1,286   12/12
 unicode_codec_pipeline     group_a  PASS      1       779    8/8
 unicode_template_renderer  group_a  PASS      1       987    9/9
 validation_chain           group_b  FAIL      2     4,154    4/6  ✗ F6
 version_sort               group_b  PASS      1     1,627    7/7
 xrange_iteration           clean    PASS      1       738    7/7
 zip_exhaustion             clean    PASS      2     2,970    5/5
 zip_pad                    group_b  PASS      1       697    6/6
```

#### Failure analysis

Same two cases, same category, same root cause as Gemini. See F6 diagnosis in
the Gemini section above. Both failures confirmed by a capture re-run at
temperature=0 (see `capture_f6_claude.py`).

**`error_translator` — F6, OSCILLATION, 3/6 oracle**

Captured migrated source:
```python
def load_config(config_dict, key):
    try:
        return config_dict[key]
    except KeyError as e:
        raise AppError('missing config key: ' + str(e))

def parse_int(s):
    try:
        return int(s)
    except ValueError as e:
        raise AppError('invalid integer: ' + str(e))

def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError as e:
        raise AppError('division by zero')
```

All three `except E, e:` clauses converted to `except E as e:` correctly.
None of the three re-raises include `from None`. Failing assertions:
`AppError(...).__context__` is `KeyError`, `ValueError`, and
`ZeroDivisionError` respectively — not `None`.

**`validation_chain` — F6, OSCILLATION, 4/6 oracle**

Captured migrated source:
```python
def validate_age(raw):
    try:
        age = int(raw)
    except ValueError as e:
        raise ValidationError('age must be an integer')
    ...

def parse_record(data):
    try:
        ...
    except (ValidationError, ParseError) as e:
        raise ParseError('invalid record: ' + str(e))
```

Both `except ..., e:` clauses converted correctly; neither re-raise uses
`from None`. `ValidationError('age must be an integer').__context__` is
`ValueError`; `ParseError(...).__context__` is `ValidationError`.

---

### Cross-model comparison

| | Gemini 2.5 Flash | Claude Sonnet 4.6 |
|---|---|---|
| Overall | 39/41 = **95.1%** | 39/41 = **95.1%** |
| Clean / mechanical | 21/21 = 100% | 21/21 = 100% |
| Group A — Undecidable | 12/12 = 100% | 12/12 = 100% |
| Group B — Decidable hard | 4/6 = 66.7% | 4/6 = 66.7% |
| Multi-trap | 2/2 = 100% | 2/2 = 100% |
| Failures | error_translator, validation_chain | error_translator, validation_chain |
| Total tokens | 122,748 | 67,527 |

Byte-identical pass/fail across all 41 cases. The two models that differ by a
full capability tier agree on every single case — including the two failures.
The F6 gap (omitting `raise ... from None` on exception re-raises) appears in
both and is unaffected by repair-loop pressure in either. That this failure is
shared across two models from different providers suggests it may be a property
of LLM exception-semantic reasoning rather than any one model — though n=2
across 2 providers means the claim is suggestive, not conclusive.

Secondary finding: Claude achieves the same score at roughly 55% of Gemini's
token cost (67K vs 123K tokens across 41 cases).
