"""Benchmark corpus metadata: band assignments for per-band scorecard reporting.

Bands:
  clean   — mechanical Py2→3 transforms; no semantic trap; failures are surprising.
  group_a — Group A: undecidable from source (F1 str/bytes, F2 division intent, F7 unicode_literals).
             A failure here is an expected limitation of the problem.
  group_b — Group B: decidable but high-miss-risk (F4 map(None,...), F5 __cmp__, F6 exc context).
             A failure here is a limitation of the agent.
  multi   — Multi-trap modules (two interacting traps); higher failure probability.
"""

from __future__ import annotations

# Maps case directory name → band string.
CASE_BANDS: dict[str, str] = {
    # ── Starter cases (7) ──────────────────────────────────────────────────
    "integer_division":     "group_a",   # F2 — floor division; docstring-assisted
    "dict_view_index":      "clean",     # docstring-assisted
    "str_bytes":            "group_a",   # F1 — docstring-assisted (see L1)
    "dict_iteration":       "clean",     # docstring-assisted
    "exception_syntax":     "clean",     # docstring-assisted
    "map_iterator":         "clean",     # docstring-assisted
    "text_encoding":        "group_a",   # F1 — docstring-assisted

    # ── Group A: F1 — str/bytes (4 new) ────────────────────────────────────
    "http_body_processor":  "group_a",
    "frame_buffer":         "group_a",
    "csv_field_builder":    "group_a",   # coin-flip-by-construction; see case notes
    "config_value_encoder": "group_a",

    # ── Group A: F2 — integer division preservation-under-temptation (3 new)
    "success_rate":         "group_a",
    "bandwidth_estimator":  "group_a",
    "sliding_average":      "group_a",

    # ── Group A: F7 — unicode_literals (2 new) ─────────────────────────────
    "unicode_template_renderer": "group_a",
    "unicode_codec_pipeline":    "group_a",

    # ── Group B: F4 — map(None,...) zip-pad (2 new) ─────────────────────────
    "zip_pad":       "group_b",
    "column_merger": "group_b",

    # ── Group B: F5 — __cmp__ / cmp() (2 new) ──────────────────────────────
    "version_sort": "group_b",
    "priority_task": "group_b",

    # ── Group B: F6 — exception context on re-raise (2 new) ────────────────
    "error_translator": "group_b",
    "validation_chain": "group_b",

    # ── Multi-trap (2 new) ──────────────────────────────────────────────────
    "report_builder":    "multi",
    "legacy_io_handler": "multi",

    # ── Clean / mechanical (17 new) ─────────────────────────────────────────
    "print_function":        "clean",
    "xrange_iteration":      "clean",
    "has_key_method":        "clean",
    "raise_comma_syntax":    "clean",
    "reduce_builtin":        "clean",
    "iterator_next":         "clean",
    "long_integer":          "clean",
    "octal_literal":         "clean",
    "metaclass_declaration": "clean",
    "raw_input_call":        "clean",
    "itertools_izip_imap":   "clean",
    "basestring_isinstance": "clean",
    "string_module_attrs":   "clean",
    "exec_statement":        "clean",
    "zip_exhaustion":        "clean",
    "apply_builtin":         "clean",
    "cmp_builtin":           "clean",
}

# Display labels for the scorecard per-band summary.
BAND_LABELS: dict[str, str] = {
    "clean":   "Clean / mechanical",
    "group_a": "Group A — Undecidable from source",
    "group_b": "Group B — Decidable, high-miss-risk",
    "multi":   "Multi-trap",
}

# Canonical band order for the scorecard.
BAND_ORDER = ["clean", "group_a", "group_b", "multi"]
