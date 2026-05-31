# Contributing to CodeShift

Thanks for your interest. CodeShift is a research-grade migration tool with a
behavioral benchmark corpus — contributions to either are welcome.

---

## Quick orientation

```
agent/         LLM repair loop — the core migration engine
analyzer/      parso-based static analyzer — flags Py2 constructs
benchmark/     41-case behavioral benchmark (source + oracle per case)
sandbox/       subprocess runners for the test-feedback loop
tests/         unit tests (mock LLM, no API keys needed)
```

The benchmark cases in `benchmark/cases/` are the most contributor-friendly
entry point. Adding a new case requires no LLM knowledge — just Py2/Py3
semantics and pytest.

---

## Setting up

```bash
git clone https://github.com/gkhurana21/codeshift.git
cd codeshift
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add keys if you want to run the LLM agent
```

Verify everything works:
```bash
pytest tests/ -v            # should be all green, no API keys needed
```

---

## Running the tests

### Unit tests (always required, no API keys)

```bash
pytest tests/
```

These use `FakeChatModel` to script LLM responses — zero real API calls.
All PRs must keep these green.

### Oracle bite-check (required for benchmark PRs)

Every oracle in `benchmark/cases/` must **fail** on its unmigrated
`source_py2.py` when run under Python 3. This proves the oracle tests
the trap rather than passing trivially.

```bash
# Run a single case bite-check:
pytest benchmark/cases/my_new_case/test_behavior.py -v
# Expected: all FAILED (not passed)
```

CI runs this automatically on every PR. A passing oracle = a broken oracle.

### Full benchmark run (manual, paid API keys)

```bash
# Gemini free tier:
CODESHIFT_MODEL=gemini-2.5-flash python -m benchmark.run_all

# Claude (canonical measurement):
python -m benchmark.run_all --model claude-sonnet-4-6
```

**Do not re-run the benchmark to improve a score.** The benchmark is a
measurement tool, not a tuning harness. Run it once, report the result
verbatim. If you change the agent and want a new score, that's a new single
run of all 41 cases, documented alongside the previous result.

---

## Adding a benchmark case

See [`benchmark/README.md`](benchmark/README.md) for the full guide, including
oracle integrity rules, band assignment, and the PR checklist.

Short version:

1. Create `benchmark/cases/{name}/source_py2.py` and `test_behavior.py`
2. Every oracle assertion must **fail** on the unmigrated source (bite-check)
3. Add `"{name}": "band"` to `benchmark/metadata.py`
4. Run `pytest benchmark/cases/{name}/test_behavior.py -v` — all FAILED = good

---

## Making a good PR

**For benchmark cases:**
- [ ] `source_py2.py` is valid Py2.7 (parseable by parso 0.7.1)
- [ ] Bite-check passes (all assertions fail on unmigrated source)
- [ ] No comments or docstrings that name the trap (keeps test integrity honest)
- [ ] Band assignment in `metadata.py` with a one-line justification comment
- [ ] Case name describes what the code *does*, not what the trap *is*

**For agent / analyzer changes:**
- [ ] Unit tests updated or added in `tests/`
- [ ] `pytest tests/` green
- [ ] If behavior changes: note expected benchmark impact in the PR description

**General:**
- Keep PRs focused — one case or one agent fix per PR
- If you're unsure about a band assignment (group_a vs group_b), explain your
  reasoning in the PR — it's a judgment call and discussion is welcome
- Do not bump the `parso` version without re-validating the full analyzer suite.
  `parso==0.7.1` is pinned because it is the only release with `grammar27.txt`
  for Python 2.7 parsing. See `requirements.txt`.

---

## Good first issues

New to the project? These are well-scoped starting points:

- **Add a `str_bytes` variant without documenting docstrings** — the current
  `str_bytes` case passes partly because its docstrings explicitly describe
  byte semantics. A variant with no such hints would measure raw F1 competence.
  See Known Limitation L1 in the README.

- **Automate the bite-check as a standalone script** — `benchmark/run_all.py`
  supports `--bite-check` as a conceptual flag but doesn't implement it yet.
  Add it: run all oracles against their unmigrated sources, assert all fail,
  exit 0 only if the check is clean.

- **Add an F4 case (`map(None, ...)` zip-pad idiom)** — the pre-registered
  failure category F4 has no benchmark case yet. The correct Py3 equivalent
  is `itertools.zip_longest`. See `benchmark/README.md` → Pre-registered
  failure taxonomy.

---

## Code style

- Python 3.9+ syntax throughout (no walrus operator in public-facing code yet)
- Type hints on all public functions
- Module-level docstrings on every new file
- Log with `logging.getLogger("codeshift.<module>")` — never `print()` in
  library code
- No hardcoded API keys anywhere. Ever. Keys live in `.env` only.

---

## Questions?

Open an issue. If you're building something interesting on top of CodeShift
(a new LLM backend, a different oracle strategy, a corpus extension), a
discussion issue before writing code saves everyone time.
