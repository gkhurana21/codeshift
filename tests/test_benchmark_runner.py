"""Unit tests for Phase 3b benchmark runner and scorecard.

No real API calls. Three layers of coverage:
  1. format_scorecard() — pure function, tested with mock CaseResult data.
  2. discover_cases()   — filesystem scan, verified against the real corpus.
  3. run_case()         — integration with FakeChatModel + real subprocess oracle;
                          covers PASS, FAIL (wrong code), and ERROR (missing files).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from agent.llm import FakeChatModel, LLMResponse, QuotaExhaustedError
from agent.schemas import TokenUsage
from benchmark.runner import CaseResult, discover_cases, run_case
from benchmark.run_all import format_scorecard, main
from sandbox.hardened import HardenedSubprocessSandbox


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(
    name: str,
    status: str,
    iters: int = 1,
    tokens: int = 500,
    passed: int = 3,
    total: int = 3,
    root_cause: str = "",
    duration_s: float = 1.5,
) -> CaseResult:
    failed = total - passed if status != "PASS" else 0
    return CaseResult(
        name=name,
        status=status,
        migration_status="OK" if status == "PASS" else "FAILED",
        oracle_passed=passed,
        oracle_failed=failed,
        oracle_total=total,
        iterations=iters,
        tokens=tokens,
        root_cause=root_cause,
        duration_s=duration_s,
    )


def _write_case(tmp: Path, source: str, oracle: str) -> Path:
    """Write source_py2.py + test_behavior.py into tmp; return the case dir."""
    (tmp / "source_py2.py").write_text(source, encoding="utf-8")
    (tmp / "test_behavior.py").write_text(oracle, encoding="utf-8")
    return tmp


# ---------------------------------------------------------------------------
# 1. format_scorecard — pure function, no subprocess
# ---------------------------------------------------------------------------

class TestFormatScorecard:
    def test_all_pass_shows_100_percent(self):
        results = [
            _make_result("integer_division", "PASS", iters=1, tokens=1200),
            _make_result("dict_view_index",  "PASS", iters=1, tokens=1100),
            _make_result("map_iterator",     "PASS", iters=2, tokens=2300),
        ]
        out = format_scorecard(results, model="gemini-2.5-flash")
        assert "3 PASS" in out
        assert "0 FAIL" in out
        assert "pass rate: 100.0%" in out
        assert "FAILURES" not in out

    def test_mixed_shows_correct_rate(self):
        results = [
            _make_result("integer_division", "PASS"),
            _make_result("str_bytes",        "FAIL", passed=0, total=7,
                         root_cause="TypeError: ord() expected string of length 1, but int found"),
            _make_result("map_iterator",     "PASS"),
        ]
        out = format_scorecard(results, model="gemini-2.5-flash")
        assert "2 PASS" in out
        assert "1 FAIL" in out
        assert "pass rate: 66.7%" in out

    def test_failure_table_shows_root_cause(self):
        results = [
            _make_result("str_bytes", "FAIL", passed=0, total=7,
                         root_cause="TypeError: ord() expected string of length 1, but int found"),
        ]
        out = format_scorecard(results, model="test-model")
        assert "FAILURES (1)" in out
        assert "str_bytes" in out
        assert "TypeError" in out
        assert "ord()" in out

    def test_error_status_shown_in_table(self):
        results = [
            _make_result("broken_case", "ERROR", root_cause="missing source_py2.py"),
        ]
        out = format_scorecard(results, model="test-model")
        assert "ERROR" in out
        assert "FAILURES (1)" in out
        assert "missing source_py2.py" in out

    def test_table_has_per_case_row(self):
        results = [
            _make_result("integer_division", "PASS", iters=1, tokens=1234, passed=6, total=6),
            _make_result("str_bytes",        "FAIL", iters=5, tokens=8000, passed=0, total=7,
                         root_cause="TypeError"),
        ]
        out = format_scorecard(results, model="gemini-2.5-flash")
        # Both case names must appear as table rows
        assert "integer_division" in out
        assert "str_bytes" in out
        # Token and iteration counts must appear
        assert "1234" in out
        assert "8000" in out

    def test_empty_results_shows_zero_rate(self):
        out = format_scorecard([], model="test-model")
        assert "pass rate: 0.0%" in out

    def test_per_band_section_present(self):
        results = [
            _make_result("integer_division", "PASS"),   # group_a
            _make_result("dict_view_index",  "PASS"),   # clean
            _make_result("zip_pad",          "FAIL", passed=0, total=3,
                         root_cause="TypeError"),       # group_b
            _make_result("report_builder",   "FAIL", passed=0, total=5,
                         root_cause="NameError"),       # multi
        ]
        out = format_scorecard(results, model="test-model")
        # All four bands must appear
        assert "Clean / mechanical" in out
        assert "Group A" in out
        assert "Group B" in out
        assert "Multi-trap" in out
        # A known-pass band must show 100%
        assert "100.0%" in out


# ---------------------------------------------------------------------------
# 2. discover_cases — filesystem, checks real corpus
# ---------------------------------------------------------------------------

class TestDiscoverCases:
    def test_finds_all_41_corpus_cases(self):
        cases = discover_cases()
        names = {c.name for c in cases}
        expected = {
            # Starter (7)
            "integer_division", "dict_view_index", "str_bytes",
            "dict_iteration", "exception_syntax", "map_iterator", "text_encoding",
            # Group A — F1 str/bytes (4)
            "http_body_processor", "frame_buffer", "csv_field_builder",
            "config_value_encoder",
            # Group A — F2 division (3)
            "success_rate", "bandwidth_estimator", "sliding_average",
            # Group A — F7 unicode_literals (2)
            "unicode_template_renderer", "unicode_codec_pipeline",
            # Group B — F4 map(None,...) (2)
            "zip_pad", "column_merger",
            # Group B — F5 __cmp__/cmp() (2)
            "version_sort", "priority_task",
            # Group B — F6 exception context (2)
            "error_translator", "validation_chain",
            # Multi-trap (2)
            "report_builder", "legacy_io_handler",
            # Clean / mechanical (17)
            "print_function", "xrange_iteration", "has_key_method",
            "raise_comma_syntax", "reduce_builtin", "iterator_next",
            "long_integer", "octal_literal", "metaclass_declaration",
            "raw_input_call", "itertools_izip_imap", "basestring_isinstance",
            "string_module_attrs", "exec_statement", "zip_exhaustion",
            "apply_builtin", "cmp_builtin",
        }
        assert names == expected, (
            f"corpus mismatch.\n"
            f"  extra  : {names - expected}\n"
            f"  missing: {expected - names}"
        )

    def test_returns_only_dirs_with_both_files(self):
        cases = discover_cases()
        for c in cases:
            assert (c / "source_py2.py").exists(), f"{c.name} missing source_py2.py"
            assert (c / "test_behavior.py").exists(), f"{c.name} missing test_behavior.py"

    def test_custom_dir_returns_subset(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            good = tmp / "good_case"
            good.mkdir()
            (good / "source_py2.py").write_text("x = 1\n")
            (good / "test_behavior.py").write_text("def test_x(): pass\n")
            # Directory without files should be excluded
            (tmp / "empty_dir").mkdir()
            cases = discover_cases(tmp)
        assert len(cases) == 1
        assert cases[0].name == "good_case"


# ---------------------------------------------------------------------------
# 3. run_case — integration with FakeChatModel (no real API calls)
# ---------------------------------------------------------------------------

class TestRunCase:
    def test_pass_when_fake_llm_returns_valid_migration(self):
        """FakeChatModel returns correct Py3 code; oracle passes; status=PASS."""
        source = (
            "def add(a, b):\n"
            "    return a + b\n"
            "\n"
            "def greet(name):\n"
            "    return 'Hello, ' + name\n"
        )
        oracle = (
            "from source_py2 import add, greet\n"
            "\n"
            "def test_add():\n"
            "    assert add(2, 3) == 5\n"
            "\n"
            "def test_greet():\n"
            "    assert greet('World') == 'Hello, World'\n"
        )
        # The source is already valid Py3; FakeChatModel returns it unchanged.
        fake = FakeChatModel(responses=[source])
        sandbox = HardenedSubprocessSandbox()

        with tempfile.TemporaryDirectory() as tmp:
            case_dir = _write_case(Path(tmp), source, oracle)
            result = run_case(case_dir, fake, sandbox, max_iterations=3)

        assert result.status == "PASS", f"expected PASS, got {result.status!r}; root_cause={result.root_cause!r}"
        assert result.oracle_passed == 2
        assert result.oracle_total == 2
        assert result.iterations == 1

    def test_fail_when_fake_llm_returns_wrong_code(self):
        """FakeChatModel returns semantically wrong code; oracle fails; status=FAIL with root_cause."""
        source = (
            "def multiply(a, b):\n"
            "    return a * b\n"
        )
        oracle = (
            "from source_py2 import multiply\n"
            "\n"
            "def test_multiply():\n"
            "    assert multiply(3, 4) == 12\n"
        )
        # LLM returns subtraction instead of multiplication — valid Py3 but wrong behavior
        wrong_v1 = "def multiply(a, b):\n    return a - b\n"
        wrong_v2 = "def multiply(a, b):\n    return a + b\n"
        fake = FakeChatModel(responses=[wrong_v1, wrong_v2])
        sandbox = HardenedSubprocessSandbox()

        with tempfile.TemporaryDirectory() as tmp:
            case_dir = _write_case(Path(tmp), source, oracle)
            result = run_case(case_dir, fake, sandbox, max_iterations=2)

        assert result.status == "FAIL", f"expected FAIL, got {result.status!r}"
        assert result.oracle_passed == 0
        assert result.root_cause != "", "expected non-empty root_cause on failure"
        # Root cause should mention the failed assertion
        assert "assert" in result.root_cause.lower() or "AssertionError" in result.root_cause

    def test_error_on_missing_files(self):
        """run_case returns ERROR immediately when source or oracle is absent."""
        fake = FakeChatModel(responses=["def x(): pass\n"])
        sandbox = HardenedSubprocessSandbox()

        with tempfile.TemporaryDirectory() as tmp:
            empty_dir = Path(tmp)
            result = run_case(empty_dir, fake, sandbox)

        assert result.status == "ERROR"
        assert "missing" in result.root_cause.lower()

    def test_quota_error_propagates_through_run_case(self):
        """QuotaExhaustedError from the LLM must NOT be swallowed as a CaseResult ERROR.

        The broad ``except Exception`` in run_case used to catch everything;
        the explicit ``except QuotaExhaustedError: raise`` guard must now let
        it escape so the benchmark runner's main loop can halt cleanly.
        """
        class QuotaLLM:
            """Fake LLM that raises QuotaExhaustedError on first invoke."""
            def invoke(self, system: str, user: str) -> LLMResponse:
                raise QuotaExhaustedError("Gemini quota/rate-limit exceeded: 429 free tier")

        sandbox = HardenedSubprocessSandbox()
        source = "def x():\n    return 1\n"
        oracle = "from source_py2 import x\ndef test_x():\n    assert x() == 1\n"

        with tempfile.TemporaryDirectory() as tmp:
            case_dir = _write_case(Path(tmp), source, oracle)
            with pytest.raises(QuotaExhaustedError, match="quota"):
                run_case(case_dir, QuotaLLM(), sandbox)

    def test_case_result_name_matches_dir(self):
        """The CaseResult.name is set to the case directory name."""
        source = "def x():\n    return 1\n"
        oracle = "from source_py2 import x\ndef test_x():\n    assert x() == 1\n"
        fake = FakeChatModel(responses=[source])
        sandbox = HardenedSubprocessSandbox()

        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp) / "my_test_case"
            case_dir.mkdir()
            _write_case(case_dir, source, oracle)
            result = run_case(case_dir, fake, sandbox)

        assert result.name == "my_test_case"


# ---------------------------------------------------------------------------
# 4. Quota-exhaustion guard — main() halts cleanly on 429
# ---------------------------------------------------------------------------

class TestQuotaHaltMain:
    """Verify that a provider 429 stops the whole run with exit code 3.

    All assertions use unittest.mock to avoid any real API calls or filesystem
    case discovery. The run_case() function is patched to raise
    QuotaExhaustedError after returning one good result, simulating a quota
    wall mid-run.
    """

    def _two_case_dirs(self) -> list:
        """Return two dummy Path objects to stand in for case directories."""
        return [Path("/fake/case_a"), Path("/fake/case_b")]

    def test_main_returns_exit_code_3_on_quota_error(self, tmp_path, capsys):
        """main() returns 3 (not 0 or 1) when QuotaExhaustedError is raised."""
        good_result = _make_result("case_a", "PASS")

        def fake_run_case(case_dir, llm, sandbox, **kwargs):
            if case_dir.name == "case_a":
                return good_result
            raise QuotaExhaustedError("Gemini quota/rate-limit exceeded: 429 free tier")

        with (
            patch("benchmark.run_all.discover_cases", return_value=self._two_case_dirs()),
            patch("benchmark.run_all.build_llm_client"),
            patch("benchmark.run_all.HardenedSubprocessSandbox"),
            patch("benchmark.run_all.run_case", side_effect=fake_run_case),
        ):
            exit_code = main(["--model", "gemini-2.5-flash"])

        assert exit_code == 3

    def test_main_prints_halt_message_to_stderr(self, tmp_path, capsys):
        """The quota-halt message names how many cases ran before the wall."""
        good_result = _make_result("case_a", "PASS")

        def fake_run_case(case_dir, llm, sandbox, **kwargs):
            if case_dir.name == "case_a":
                return good_result
            raise QuotaExhaustedError("429 free tier daily limit")

        with (
            patch("benchmark.run_all.discover_cases", return_value=self._two_case_dirs()),
            patch("benchmark.run_all.build_llm_client"),
            patch("benchmark.run_all.HardenedSubprocessSandbox"),
            patch("benchmark.run_all.run_case", side_effect=fake_run_case),
        ):
            main(["--model", "gemini-2.5-flash"])

        err = capsys.readouterr().err
        assert "QUOTA EXHAUSTED" in err
        assert "1/2" in err          # completed/total cases shown

    def test_main_prints_partial_scorecard_before_halt(self, tmp_path, capsys):
        """When at least one case ran, the partial scorecard is printed to stdout."""
        good_result = _make_result("case_a", "PASS")

        def fake_run_case(case_dir, llm, sandbox, **kwargs):
            if case_dir.name == "case_a":
                return good_result
            raise QuotaExhaustedError("429 free tier daily limit")

        with (
            patch("benchmark.run_all.discover_cases", return_value=self._two_case_dirs()),
            patch("benchmark.run_all.build_llm_client"),
            patch("benchmark.run_all.HardenedSubprocessSandbox"),
            patch("benchmark.run_all.run_case", side_effect=fake_run_case),
        ):
            main(["--model", "gemini-2.5-flash"])

        out = capsys.readouterr().out
        # Partial scorecard must appear: the one completed case shows up
        assert "case_a" in out
        assert "PASS" in out

    def test_main_no_scorecard_when_first_case_quota_errors(self, tmp_path, capsys):
        """If the very first case hits quota, no scorecard is printed (nothing ran)."""
        def fake_run_case(case_dir, llm, sandbox, **kwargs):
            raise QuotaExhaustedError("429 free tier daily limit")

        with (
            patch("benchmark.run_all.discover_cases", return_value=self._two_case_dirs()),
            patch("benchmark.run_all.build_llm_client"),
            patch("benchmark.run_all.HardenedSubprocessSandbox"),
            patch("benchmark.run_all.run_case", side_effect=fake_run_case),
        ):
            exit_code = main(["--model", "gemini-2.5-flash"])

        out = capsys.readouterr().out
        assert exit_code == 3
        assert out == ""   # nothing to report — zero cases completed
