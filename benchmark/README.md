# Benchmark Suite

A 41-case behavioral benchmark for verifying Python 2→3 migration correctness.
Each case is a hand-authored pair: a Py2 source file and a behavioral oracle
that encodes what the program *actually does*, not just whether it parses.

---

## What this measures

The benchmark tests **behavioral correctness**, not syntactic validity.

A migration that turns `reduce(f, lst)` into `functools.reduce(f, lst)` passes
a syntax check. The oracle goes further: it runs the migrated code and asserts
on actual return values, exception types, and side effects — the same results
the Py2 program would have produced.

This catches semantic traps that syntax-only tools miss:
- `a / b` on integers silently floor-divides in Py2 — a correct migration uses `//`
- `except KeyError, e:` → `except KeyError as e:` is necessary but not sufficient —
  re-raises also need `from None` to suppress `__context__`
- `map(None, a, b)` is a zip-pad idiom in Py2 with no direct Py3 equivalent

### How to read the band labels

Cases are grouped into bands that make different claims:

| Band | Claim if passing |
|---|---|
| **clean** | Mechanical rewrite; any correct tool should pass |
| **group_a** | Undecidable from source — pass = oracle alignment on one defensible interpretation, not recovered intent |
| **group_b** | Decidable but high-miss-risk — pass = agent found the correct non-obvious transform; fail = agent limitation |
| **multi** | Multiple traps in one file |

A blended pass rate hides this structure. 100% on group_a does not mean the
agent resolves genuine ambiguity — it means the agent's arbitrary choice
matched the oracle's arbitrary pin. See the main README for the full discussion.

---

## Running the benchmark

```bash
# Full 41-case run (Gemini free tier):
CODESHIFT_MODEL=gemini-2.5-flash python -m benchmark.run_all

# Full run with Claude (paid):
python -m benchmark.run_all --model claude-sonnet-4-6

# Specific cases only:
python -m benchmark.run_all --cases error_translator,validation_chain

# Dry-run to list discovered cases without running:
python -m benchmark.run_all --list
```

**One run, report verbatim.** The benchmark is a measurement tool, not a
tuning harness. Do not re-run until a score improves — that turns a measurement
into a search. If you change the agent and want a new number, that's a new run
of the full 41 cases, reported alongside the previous result.

### Bite-check (oracle integrity)

Every oracle must fail on the *unmigrated* source when run under Python 3.
This verifies the oracle is actually testing the right thing, not passing
trivially.

```bash
# Run the bite-check against all cases:
python -m benchmark.run_all --bite-check

# Or manually for a single case:
python -m pytest benchmark/cases/my_new_case/test_behavior.py \
    --override-ini="python_files=test_*.py" \
    # source_py2.py must be in the same dir — unmigrated
```

The bite-check passes when all oracles *fail* (SyntaxError, NameError,
AssertionError, etc.). A passing oracle on unmigrated source means the test
does not exercise the trap and must be rewritten.

---

## How to add a case

### 1. Choose a trap

Each case targets **exactly one semantic trap**. No two cases share a trap.
Before writing, check `benchmark/metadata.py` to confirm the trap is not
already covered.

### 2. Create the files

```
benchmark/cases/{name}/
    source_py2.py      # Py2 source — must parse under parso 0.7.1 as py2.7
    test_behavior.py   # Behavioral oracle
```

`{name}` should be a snake_case description of what the file does, not the
trap it tests (e.g., `integer_division`, not `floor_division_trap`).

### 3. Write the source

- Must be valid Python 2.7 syntax (parseable by parso 0.7.1 with `version="2.7"`)
- Should look like real production code — no `# THIS IS A TRAP` comments
- Keep it short: 15–40 lines is typical. The agent reads the whole file as context

### 4. Write the oracle

Oracle rules (all are mandatory):

- **Every assertion must fail on the unmigrated source** under Python 3.
  The only exception: `pytest.raises` guards for error paths that fire
  identically in Py2 and Py3.
- **No assertion may pass on a syntax-only migration** if the trap is semantic.
  For integer division, use inputs that don't divide evenly. For dict views,
  use multi-step operations that fail on a view but pass on a list.
- **No ordering-sensitive assertions on multi-element dicts.** Py2 dict
  iteration order is arbitrary. Assert on `sorted()` output or use
  single-element dicts.
- **`__context__` assertions use `is None`** (identity, not equality).

Template:
```python
"""Behavioral oracle for {name}.

Trap: {one sentence describing the Py2/Py3 semantic difference}.
All assertions below must FAIL on the unmigrated source_py2.py under Python 3.
"""
import pytest
# Import from the source file (runner copies it into the work dir):
from source_py2 import my_function


def test_basic_case():
    assert my_function(2, 3) == 1   # floor: 5//2 in Py2, not 2.5


def test_edge_case():
    assert my_function(1, 2) == 0   # floor: 1//2 in Py2
```

### 5. Assign a band in metadata.py

Open `benchmark/metadata.py` and add your case to `CASE_BANDS`:

```python
"my_new_case": "clean",   # or "group_a", "group_b", "multi"
```

**Band assignment guide:**

- `clean` — the correct Py3 transform is unambiguous and mechanical
  (rename a builtin, fix `print` syntax, replace `xrange`). Any correct
  tool should pass.
- `group_a` — the source does not contain enough information to determine
  the single correct Py3 equivalent. The oracle pins one defensible
  interpretation; a different oracle pinning the other interpretation would
  also be valid.
- `group_b` — a correct Py3 transform exists and is derivable from the
  source alone, but requires recognising a specific idiom or coordinating
  changes across multiple sites. An agent may fail.
- `multi` — the case exercises two or more distinct traps from different
  categories simultaneously.

If you're unsure between `group_a` and `group_b`, ask: *given only the source
file, is there a single correct answer?* Yes → `group_b`. No → `group_a`.

### 6. Bite-check before submitting

```bash
# Must print FAILURES (not passes) for your new case:
pytest benchmark/cases/my_new_case/test_behavior.py -v
# (run against unmigrated source — the source_py2.py in the case dir)
```

All assertions must fail. If any pass, the oracle is not testing the trap.

### 7. PR checklist

- [ ] `source_py2.py` parses under `parso.load_grammar(version="2.7")`
- [ ] `test_behavior.py` — every assertion fails on unmigrated source (bite-check green)
- [ ] No docstring or comment names the trap (e.g. avoid `# this is the F6 trap`)
- [ ] Band assignment in `metadata.py` with a one-line justification comment
- [ ] No ordering-sensitive assertions on multi-element dicts
- [ ] Case name describes what the code does, not what the trap is

---

## Case inventory

See `benchmark/metadata.py` for the full band-annotated list of all 41 cases.

---

## Pre-registered failure taxonomy

The failure categories below were written before any full-corpus run.
Each failure in a benchmark run is mapped to one of these, or flagged as
surprising. See the main README for the full descriptions.

| Category | Band | Description |
|---|---|---|
| F1 | group_a | `str`/`bytes` intent ambiguous at call boundary |
| F2 | group_a | Integer division where float was intended |
| F4 | group_b | `map(None, ...)` zip-pad idiom |
| F5 | group_b | `__cmp__` / `cmp()` builtin removal |
| F6 | group_b | Exception context on re-raise — missing `from None` |
| F7 | group_a | `unicode_literals` future import interaction |
