"""Detection rules for Python 2 constructs.

Design notes:
- Each detector is a small function that walks the parso tree (or scans tokens)
  and returns a list of `Finding`s.
- Some detections are inherently undecidable from static analysis (e.g. whether
  `a / b` is `int / int`). Those are flagged as best-effort heuristics with a
  `notes` field; the agent in Phase 2 is the final reasoner.
- `<>` is not accepted by parso's grammar27, so we cover it (and a couple of
  other awkward tokens) via a token-level fallback.
"""

from __future__ import annotations

import re
import tokenize
import io
from typing import Iterable, List, Optional

from parso.python.tree import Module

from analyzer.constants import (
    DICT_PY2_METHODS,
    FUTURE_NEUTRALIZES_INT_DIV,
    REMOVED_BUILTIN_NAMES,
    STDLIB_RENAMES,
)
from analyzer.schema import Category, Finding, Severity


# --- helpers -----------------------------------------------------------------

_INT_LITERAL_RE = re.compile(r"^[+-]?\d+[lL]?$")
_OCTAL_PY2_RE = re.compile(r"^0[0-7]+[lL]?$")


def _walk(node):
    """Yield every node in the tree (depth-first)."""
    yield node
    for child in getattr(node, "children", []):
        yield from _walk(child)


def _snippet(node) -> str:
    """One-line snippet for the finding. Strips parso's leading prefix (comments / whitespace)."""
    if hasattr(node, "get_code"):
        try:
            code = node.get_code(include_prefix=False)
        except TypeError:
            code = node.get_code()
    else:
        code = getattr(node, "value", "")
    code = code.strip()
    # Collapse multi-line snippets to a single line so the table stays readable.
    if "\n" in code:
        code = code.splitlines()[0].rstrip() + " ..."
    if len(code) > 120:
        code = code[:117] + "..."
    return code


def _line_col(node) -> tuple[int, int]:
    return node.start_pos  # (line, col), line is 1-based


def _looks_like_int_literal(text: str) -> bool:
    return bool(_INT_LITERAL_RE.match(text))


# --- 0. __future__ imports ---------------------------------------------------

def collect_future_flags(tree: Module) -> List[str]:
    """Return the list of __future__ feature names imported in the file."""
    flags: List[str] = []
    for node in _walk(tree):
        if node.type != "import_from":
            continue
        # Look for `from __future__ import X[, Y]`
        # parso shape: keyword 'from' name '__future__' keyword 'import' <names>
        kids = list(node.children)
        if len(kids) >= 4 and kids[1].type == "name" and kids[1].value == "__future__":
            # everything after the 'import' keyword
            try:
                imp_idx = next(i for i, c in enumerate(kids) if c.type == "keyword" and c.value == "import")
            except StopIteration:
                continue
            for c in kids[imp_idx + 1:]:
                for sub in _walk(c):
                    if sub.type == "name":
                        flags.append(sub.value)
    return flags


def detect_future_imports(tree: Module) -> List[Finding]:
    out: List[Finding] = []
    for node in _walk(tree):
        if node.type != "import_from":
            continue
        kids = list(node.children)
        if len(kids) >= 2 and kids[1].type == "name" and kids[1].value == "__future__":
            line, col = _line_col(node)
            out.append(Finding(
                line=line, column=col,
                construct_type="future_import",
                category=Category.META,
                severity=Severity.INFO,
                snippet=_snippet(node),
                semantic_risk=False,
                notes="__future__ imports are noted - related detections may be neutralized.",
            ))
    return out


# --- 1. print statement vs print() -------------------------------------------

def detect_print_statements(tree: Module) -> List[Finding]:
    """Flag `print x` (Py2 statement). `print(x)` is fine and not flagged."""
    out: List[Finding] = []
    for node in _walk(tree):
        if node.type != "print_stmt":
            continue
        kids = node.children  # [keyword 'print', ...rest]
        if len(kids) == 1:
            # bare `print` - statement form, ok-ish but still Py2
            line, col = _line_col(node)
            out.append(Finding(
                line=line, column=col,
                construct_type="print_statement",
                category=Category.SYNTAX,
                severity=Severity.WARNING,
                snippet=_snippet(node),
                semantic_risk=False,
            ))
            continue
        # If the only child after `print` is an `atom` node that starts with `(`,
        # treat it as function-call form and skip.
        rest = kids[1:]
        if len(rest) == 1 and rest[0].type == "atom":
            first_child = getattr(rest[0], "children", [None])[0]
            if first_child is not None and getattr(first_child, "value", None) == "(":
                continue
        line, col = _line_col(node)
        out.append(Finding(
            line=line, column=col,
            construct_type="print_statement",
            category=Category.SYNTAX,
            severity=Severity.WARNING,
            snippet=_snippet(node),
            semantic_risk=False,
        ))
    return out


# --- 2. except / raise old-style comma ---------------------------------------

def detect_old_except(tree: Module) -> List[Finding]:
    """`except E, e:` (comma binding) - replaced by `except E as e:`."""
    out: List[Finding] = []
    for node in _walk(tree):
        if node.type != "except_clause":
            continue
        # parso shape: keyword 'except' <expr> operator ',' <name>  (old style)
        #     vs:     keyword 'except' <expr> keyword 'as' <name>   (new style)
        has_comma_binding = any(
            c.type == "operator" and c.value == "," for c in node.children
        )
        if has_comma_binding:
            line, col = _line_col(node)
            out.append(Finding(
                line=line, column=col,
                construct_type="except_comma",
                category=Category.SYNTAX,
                severity=Severity.ERROR,
                snippet=_snippet(node),
                semantic_risk=False,
            ))
    return out


def detect_old_raise(tree: Module) -> List[Finding]:
    """`raise E, 'msg'` (comma form) - replaced by `raise E('msg')`."""
    out: List[Finding] = []
    for node in _walk(tree):
        if node.type != "raise_stmt":
            continue
        # `raise` | `raise E` | `raise E, msg` | `raise E, msg, tb` | `raise E(msg)`
        has_comma = any(
            c.type == "operator" and c.value == "," for c in node.children
        )
        if has_comma:
            line, col = _line_col(node)
            out.append(Finding(
                line=line, column=col,
                construct_type="raise_comma",
                category=Category.SYNTAX,
                severity=Severity.ERROR,
                snippet=_snippet(node),
                semantic_risk=False,
            ))
    return out


# --- 3. tuple-unpacking parameters -------------------------------------------

def detect_tuple_params(tree: Module) -> List[Finding]:
    """`def f((a, b)):` removed in Py3."""
    out: List[Finding] = []
    for node in _walk(tree):
        if node.type != "fpdef":
            continue
        # fpdef can be either `name` or `( fplist )`. Tuple form starts with `(`.
        kids = node.children
        if kids and getattr(kids[0], "value", None) == "(":
            line, col = _line_col(node)
            out.append(Finding(
                line=line, column=col,
                construct_type="tuple_param",
                category=Category.SYNTAX,
                severity=Severity.ERROR,
                snippet=_snippet(node),
                semantic_risk=False,
            ))
    return out


# --- 4. exec statement, backtick repr ----------------------------------------

def detect_exec_statement(tree: Module) -> List[Finding]:
    """Flag `exec X` (statement). `exec(X)` is already Py3-compatible and not flagged."""
    out: List[Finding] = []
    for node in _walk(tree):
        if node.type != "exec_stmt":
            continue
        kids = node.children  # [keyword 'exec', <expr>, optional 'in' ns, ...]
        rest = kids[1:]
        # Function-call form: `exec ( ... )` -- single atom child starting with '('.
        if len(rest) == 1 and rest[0].type == "atom":
            first_child = getattr(rest[0], "children", [None])[0]
            if first_child is not None and getattr(first_child, "value", None) == "(":
                continue
        line, col = _line_col(node)
        out.append(Finding(
            line=line, column=col,
            construct_type="exec_statement",
            category=Category.SYNTAX,
            severity=Severity.ERROR,
            snippet=_snippet(node),
            semantic_risk=False,
            notes="exec is a function in Py3: exec(...)",
        ))
    return out


def detect_backtick_repr(tree: Module) -> List[Finding]:
    """`` `x` `` form - replaced by `repr(x)`."""
    out: List[Finding] = []
    for node in _walk(tree):
        if node.type != "atom":
            continue
        kids = node.children
        if kids and getattr(kids[0], "value", None) == "`":
            line, col = _line_col(node)
            out.append(Finding(
                line=line, column=col,
                construct_type="backtick_repr",
                category=Category.SYNTAX,
                severity=Severity.ERROR,
                snippet=_snippet(node),
                semantic_risk=False,
            ))
    return out


# --- 5. octal literal 0755 ---------------------------------------------------

def detect_old_octal(tree: Module) -> List[Finding]:
    out: List[Finding] = []
    for node in _walk(tree):
        if node.type != "number":
            continue
        val = node.value
        # 0, 0.5, 0j, 0x, 0o, 0b all OK. Only `0` + octal digits (with no o/x/b/.)
        # is the Py2 octal literal we want to flag.
        if _OCTAL_PY2_RE.match(val) and val != "0":
            line, col = _line_col(node)
            out.append(Finding(
                line=line, column=col,
                construct_type="old_octal_literal",
                category=Category.SYNTAX,
                severity=Severity.ERROR,
                snippet=val,
                semantic_risk=False,
                notes="Use 0o-prefixed octal in Py3.",
            ))
    return out


# --- 6. long literal 10L -----------------------------------------------------

def detect_long_literal(tree: Module) -> List[Finding]:
    out: List[Finding] = []
    for node in _walk(tree):
        if node.type != "number":
            continue
        if node.value.endswith(("L", "l")):
            line, col = _line_col(node)
            out.append(Finding(
                line=line, column=col,
                construct_type="long_literal",
                category=Category.SYNTAX,
                severity=Severity.ERROR,
                snippet=node.value,
                semantic_risk=False,
                notes="Py3 has only int; drop the L suffix.",
            ))
    return out


# --- 7. integer division ` / ` (semantic) ------------------------------------

def detect_integer_division(tree: Module, future_flags: Iterable[str]) -> List[Finding]:
    """Flag `/` usage as a semantic risk.

    Heuristic:
      - both operands integer literals -> high confidence flag.
      - operands include names/calls -> still flag as semantic risk, with
        notes saying operand types are unknown.
      - if `from __future__ import division` is in effect, skip (already Py3 semantics).
    """
    if FUTURE_NEUTRALIZES_INT_DIV in future_flags:
        return []
    out: List[Finding] = []
    for node in _walk(tree):
        if node.type != "term":
            continue
        kids = node.children
        i = 1
        while i < len(kids):
            op = kids[i]
            if getattr(op, "value", None) == "/":
                left = kids[i - 1]
                right = kids[i + 1] if i + 1 < len(kids) else None
                both_int_lits = (
                    left.type == "number"
                    and right is not None
                    and right.type == "number"
                    and _looks_like_int_literal(left.value)
                    and _looks_like_int_literal(right.value)
                )
                notes = (
                    "both operands are integer literals - definite int/int division"
                    if both_int_lits
                    else "operand types unknown - heuristic flag; agent should verify"
                )
                line, col = _line_col(op)
                out.append(Finding(
                    line=line, column=col,
                    construct_type="integer_division",
                    category=Category.SEMANTIC,
                    severity=Severity.WARNING if both_int_lits else Severity.INFO,
                    snippet=_snippet(node),
                    semantic_risk=True,
                    notes=notes,
                ))
            i += 2
    return out


# --- 8. dict-iteration / has_key / removed builtins / method `.next()` -------

def detect_dict_methods_and_builtins(tree: Module) -> List[Finding]:
    """Detect `.iteritems()/itervalues/iterkeys/has_key/.next()` and removed builtins.

    For removed-builtin *calls* (xrange, unicode, basestring, unichr, long, cmp,
    apply, reload, reduce, raw_input) we flag the call site.
    For `obj.iteritems()` etc. we flag the method name.
    """
    out: List[Finding] = []
    for node in _walk(tree):
        if node.type != "power":
            continue
        kids = list(node.children)
        if not kids:
            continue

        # Removed-builtin call: power = name <trailer '(' ... ')'>
        if (
            kids[0].type == "name"
            and kids[0].value in REMOVED_BUILTIN_NAMES
            and len(kids) >= 2
            and kids[1].type == "trailer"
            and getattr(kids[1].children[0], "value", None) == "("
        ):
            name = kids[0].value
            line, col = _line_col(kids[0])
            out.append(Finding(
                line=line, column=col,
                construct_type=f"removed_builtin_{name}",
                category=Category.SEMANTIC if name in {"xrange", "cmp", "reduce", "raw_input"} else Category.SYNTAX,
                severity=Severity.WARNING,
                snippet=_snippet(node),
                semantic_risk=name in {"xrange", "cmp", "reduce", "raw_input"},
                notes=f"Py3: {REMOVED_BUILTIN_NAMES[name]}.",
            ))

        # Method-style trailers: walk pairs `<trailer .NAME> <trailer ( ... )>`
        for idx in range(1, len(kids) - 1):
            t = kids[idx]
            next_t = kids[idx + 1]
            if (
                t.type == "trailer"
                and len(t.children) == 2
                and getattr(t.children[0], "value", None) == "."
                and t.children[1].type == "name"
                and next_t.type == "trailer"
                and getattr(next_t.children[0], "value", None) == "("
            ):
                method_name = t.children[1].value
                if method_name in DICT_PY2_METHODS:
                    line, col = _line_col(t.children[1])
                    out.append(Finding(
                        line=line, column=col,
                        construct_type=f"dict_method_{method_name}",
                        category=Category.SEMANTIC,
                        severity=Severity.WARNING,
                        snippet=_snippet(node),
                        semantic_risk=True,
                        notes=(
                            "Py3 has no .iteritems/itervalues/iterkeys/has_key. "
                            "Use .items()/.values()/.keys()/in operator. "
                            "These return views, not lists - watch for code that "
                            "indexes, mutates-while-iterating, or pickles the result."
                        ),
                    ))
                elif method_name == "next":
                    # `.next()` -> `next(it)`
                    line, col = _line_col(t.children[1])
                    out.append(Finding(
                        line=line, column=col,
                        construct_type="iterator_next_method",
                        category=Category.SYNTAX,
                        severity=Severity.WARNING,
                        snippet=_snippet(node),
                        semantic_risk=False,
                        notes="Py3: next(it) builtin instead of it.next().",
                    ))
    return out


# --- 9. bare-name usage of removed builtins (e.g. isinstance(x, basestring)) -

def detect_removed_builtin_names(tree: Module) -> List[Finding]:
    """Removed names appearing not as a direct call.

    Examples: `isinstance(x, basestring)`, `isinstance(x, long)`,
    `f.__class__ is unicode`, etc.

    We deliberately avoid flagging local variables shadowing these names; if a
    user wrote `cmp = something`, that's a real binding and we'd false-positive.
    To stay safe we only flag inside `arglist`, `argument`, `comparison`, and
    `atom_expr` contexts. This is best-effort.
    """
    out: List[Finding] = []
    flagged: set[tuple[int, int]] = set()
    for node in _walk(tree):
        if node.type != "name" or node.value not in REMOVED_BUILTIN_NAMES:
            continue
        parent = node.parent
        if parent is None:
            continue
        # Skip if this name is the callee (already handled by detect_dict_methods_and_builtins).
        if parent.type == "power" and parent.children and parent.children[0] is node:
            continue
        # Skip definition targets (e.g. `def long(): ...` or `long = 1`).
        if parent.type == "expr_stmt" and parent.children and parent.children[0] is node:
            continue
        if parent.type == "funcdef" and len(parent.children) > 1 and parent.children[1] is node:
            continue
        # Skip keyword-argument names: in `f(cmp=...)`, `cmp` is the kwarg name, not a reference.
        if parent.type == "argument" and parent.children and parent.children[0] is node:
            # argument shape with kwarg: <name> = <expr>
            if len(parent.children) >= 2 and getattr(parent.children[1], "value", None) == "=":
                continue
        # Skip parameter names in def f(cmp=...): the param name shadowing a builtin is fine here.
        if parent.type == "param" and parent.children and parent.children[0] is node:
            continue
        # Skip keyword-only argument bindings in `def f(*, cmp=...)`.
        if parent.type == "tfpdef" and parent.children and parent.children[0] is node:
            continue
        key = _line_col(node)
        if key in flagged:
            continue
        flagged.add(key)
        line, col = key
        out.append(Finding(
            line=line, column=col,
            construct_type=f"removed_builtin_name_{node.value}",
            category=Category.SEMANTIC if node.value in {"basestring", "unicode", "long"} else Category.SYNTAX,
            severity=Severity.WARNING,
            snippet=_snippet(node),
            semantic_risk=node.value in {"basestring", "unicode", "long", "cmp"},
            notes=f"Py3: {REMOVED_BUILTIN_NAMES[node.value]}.",
        ))
    return out


# --- 10. stdlib renames ------------------------------------------------------

def detect_stdlib_renames(tree: Module) -> List[Finding]:
    """`import urllib2`, `from StringIO import ...`, etc."""
    out: List[Finding] = []
    for node in _walk(tree):
        if node.type == "import_name":
            # children: keyword 'import' <dotted_as_names>
            for sub in _walk(node):
                if sub.type == "name" and sub.value in STDLIB_RENAMES:
                    line, col = _line_col(sub)
                    out.append(Finding(
                        line=line, column=col,
                        construct_type=f"stdlib_rename_{sub.value}",
                        category=Category.STDLIB,
                        severity=Severity.WARNING,
                        snippet=_snippet(node),
                        semantic_risk=False,
                        notes=f"Py3: use {STDLIB_RENAMES[sub.value]}.",
                    ))
                    break  # one finding per import
        elif node.type == "import_from":
            kids = node.children
            # `from X import Y` shape: keyword 'from' <dotted_name> keyword 'import' <names>
            if len(kids) >= 2:
                source = kids[1]
                # could be a name or a dotted_name
                top_name = None
                if source.type == "name":
                    top_name = source.value
                elif source.type == "dotted_name" and source.children:
                    top_name = source.children[0].value
                if top_name in STDLIB_RENAMES:
                    line, col = _line_col(source)
                    out.append(Finding(
                        line=line, column=col,
                        construct_type=f"stdlib_rename_{top_name}",
                        category=Category.STDLIB,
                        severity=Severity.WARNING,
                        snippet=_snippet(node),
                        semantic_risk=False,
                        notes=f"Py3: use {STDLIB_RENAMES[top_name]}.",
                    ))
    return out


# --- 11. map/filter/zip - len() or [] usage (semantic) -----------------------

_ITER_BUILTINS = {"map", "filter", "zip"}
_DICT_VIEW_METHODS = {"keys", "values", "items"}


def detect_iter_builtin_misuse(tree: Module) -> List[Finding]:
    """Flag cases where map/filter/zip results need list materialisation.

    Cases caught (best-effort):
      - len(map(...))     -> needs list(map(...))
      - map(...)[i]       -> needs list(map(...))[i]
      - any later .index, .append, .extend on the result is NOT caught here
        (requires flow analysis); agent should reason about it.
    """
    out: List[Finding] = []
    for node in _walk(tree):
        if node.type != "power":
            continue
        kids = list(node.children)
        if not kids:
            continue

        # Case A: len(map(...)) / len(filter(...)) / len(zip(...))
        if (
            kids[0].type == "name"
            and kids[0].value == "len"
            and len(kids) >= 2
            and kids[1].type == "trailer"
            and getattr(kids[1].children[0], "value", None) == "("
        ):
            inner = kids[1].children[1] if len(kids[1].children) >= 3 else None
            if inner is not None and inner.type == "power" and inner.children:
                head = inner.children[0]
                if head.type == "name" and head.value in _ITER_BUILTINS:
                    line, col = _line_col(head)
                    out.append(Finding(
                        line=line, column=col,
                        construct_type=f"iter_builtin_len_{head.value}",
                        category=Category.SEMANTIC,
                        severity=Severity.WARNING,
                        snippet=_snippet(node),
                        semantic_risk=True,
                        notes=f"Py3 {head.value}() returns an iterator; len() will fail. Wrap in list().",
                    ))

        # Case B: map(...)[i] etc.
        if (
            kids[0].type == "name"
            and kids[0].value in _ITER_BUILTINS
            and len(kids) >= 3
            and kids[1].type == "trailer"
            and getattr(kids[1].children[0], "value", None) == "("
            and kids[2].type == "trailer"
            and getattr(kids[2].children[0], "value", None) == "["
        ):
            line, col = _line_col(kids[0])
            out.append(Finding(
                line=line, column=col,
                construct_type=f"iter_builtin_index_{kids[0].value}",
                category=Category.SEMANTIC,
                severity=Severity.WARNING,
                snippet=_snippet(node),
                semantic_risk=True,
                notes=f"Py3 {kids[0].value}() returns an iterator; can't be indexed. Wrap in list().",
            ))
    return out


# --- 11b. dict-view misuse (.keys()[i], len(d.keys()), etc.) ----------------

def _trailing_method_call_name(power_node) -> Optional[str]:
    """If `power_node` ends with `<expr>.NAME(...)`, return NAME; else None.

    Used to identify the method on the inner expression of e.g. `len(d.keys())`.
    """
    kids = list(getattr(power_node, "children", []))
    if len(kids) < 3:
        return None
    a, b = kids[-2], kids[-1]
    if (
        a.type == "trailer"
        and len(a.children) == 2
        and getattr(a.children[0], "value", None) == "."
        and a.children[1].type == "name"
        and b.type == "trailer"
        and getattr(b.children[0], "value", None) == "("
    ):
        return a.children[1].value
    return None


def detect_dict_view_misuse(tree: Module) -> List[Finding]:
    """`d.keys()[0]` and `len(d.keys())` are real bugs in Py3 (view objects).

    Detects only the statically-obvious patterns:
      - <expr>.keys()/.values()/.items() [...]      (indexing immediately after the call)
      - len(<expr>.keys()/.values()/.items())       (len of a view)

    Other view-related issues (mutate-while-iterating, pickling a view, slicing
    later) require flow analysis - those are notes on the existing dict-method
    findings, not separate detections.
    """
    out: List[Finding] = []
    for node in _walk(tree):
        if node.type != "power":
            continue
        kids = list(node.children)

        # Pattern A: <expr>.keys()[i] - three trailers in a row at the tail.
        if len(kids) >= 4:
            for i in range(1, len(kids) - 2):
                a, b, c = kids[i], kids[i + 1], kids[i + 2]
                if (
                    a.type == "trailer"
                    and len(a.children) == 2
                    and getattr(a.children[0], "value", None) == "."
                    and a.children[1].type == "name"
                    and a.children[1].value in _DICT_VIEW_METHODS
                    and b.type == "trailer"
                    and getattr(b.children[0], "value", None) == "("
                    and c.type == "trailer"
                    and getattr(c.children[0], "value", None) == "["
                ):
                    method = a.children[1].value
                    line, col = _line_col(a.children[1])
                    out.append(Finding(
                        line=line, column=col,
                        construct_type=f"dict_view_index_{method}",
                        category=Category.SEMANTIC,
                        severity=Severity.WARNING,
                        snippet=_snippet(node),
                        semantic_risk=True,
                        notes=(
                            f"Py3 dict.{method}() returns a view, not a list - cannot be indexed. "
                            f"Wrap in list(): list(d.{method}())[i]."
                        ),
                    ))

        # Pattern B: len(<expr>.keys()/.values()/.items())
        if (
            kids
            and kids[0].type == "name"
            and kids[0].value == "len"
            and len(kids) >= 2
            and kids[1].type == "trailer"
            and getattr(kids[1].children[0], "value", None) == "("
            and len(kids[1].children) >= 3
        ):
            inner = kids[1].children[1]
            if inner.type == "power":
                method = _trailing_method_call_name(inner)
                if method in _DICT_VIEW_METHODS:
                    line, col = _line_col(inner)
                    out.append(Finding(
                        line=line, column=col,
                        construct_type=f"dict_view_len_{method}",
                        category=Category.SEMANTIC,
                        severity=Severity.INFO,
                        snippet=_snippet(node),
                        semantic_risk=True,
                        notes=(
                            f"Py3 dict.{method}() returns a view. len() works on views, but the "
                            f"idiomatic Py3 form is len(d). Flagged because mixing views and "
                            f"list-y code is a frequent source of subtle bugs."
                        ),
                    ))
    return out


# --- 12. sorted(..., cmp=...) ------------------------------------------------

def detect_sorted_cmp_kwarg(tree: Module) -> List[Finding]:
    """sorted(xs, cmp=...) - removed in Py3; use key= or functools.cmp_to_key."""
    out: List[Finding] = []
    for node in _walk(tree):
        if node.type != "power":
            continue
        kids = list(node.children)
        if not (kids and kids[0].type == "name" and kids[0].value == "sorted"):
            continue
        # Look at the argument list for `cmp=`.
        for t in kids[1:]:
            if t.type != "trailer":
                continue
            if getattr(t.children[0], "value", None) != "(":
                continue
            for sub in _walk(t):
                if sub.type != "argument":
                    continue
                sub_kids = sub.children
                if (
                    len(sub_kids) >= 3
                    and sub_kids[0].type == "name"
                    and sub_kids[0].value == "cmp"
                    and getattr(sub_kids[1], "value", None) == "="
                ):
                    line, col = _line_col(sub_kids[0])
                    out.append(Finding(
                        line=line, column=col,
                        construct_type="sorted_cmp_kwarg",
                        category=Category.SEMANTIC,
                        severity=Severity.WARNING,
                        snippet=_snippet(node),
                        semantic_risk=True,
                        notes="Py3: use functools.cmp_to_key(cmp_fn) as key= argument.",
                    ))
    return out


# --- 13. token-level fallback for `<>` ---------------------------------------

def detect_ne_operator(source: str) -> List[Finding]:
    """`<>` inequality operator - parso 0.7 rejects it, so use tokens."""
    out: List[Finding] = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenizeError, IndentationError):
        # Fall through to a simple regex if tokenizing fails.
        return _regex_ne(source)
    for i in range(len(tokens) - 1):
        t1, t2 = tokens[i], tokens[i + 1]
        if (
            t1.type == tokenize.OP and t1.string == "<"
            and t2.type == tokenize.OP and t2.string == ">"
            and t1.end == t2.start  # immediately adjacent
        ):
            line, col = t1.start
            out.append(Finding(
                line=line, column=col,
                construct_type="ne_operator",
                category=Category.SYNTAX,
                severity=Severity.ERROR,
                snippet="<>",
                semantic_risk=False,
                notes="Py3: use != instead of <>.",
            ))
    return out


def _regex_ne(source: str) -> List[Finding]:
    out: List[Finding] = []
    for i, raw in enumerate(source.splitlines(), start=1):
        # Skip string content roughly: drop quoted parts.
        cleaned = re.sub(r"(?:'[^']*'|\"[^\"]*\")", "", raw)
        for m in re.finditer(r"<>", cleaned):
            out.append(Finding(
                line=i, column=m.start(),
                construct_type="ne_operator",
                category=Category.SYNTAX,
                severity=Severity.ERROR,
                snippet="<>",
                semantic_risk=False,
                notes="Py3: use != instead of <> (regex fallback).",
            ))
    return out


# --- Coordinator -------------------------------------------------------------

def run_all(tree: Module, source: str) -> tuple[List[Finding], List[str]]:
    """Run every detector and return (findings sorted by line/col, future_flags)."""
    future_flags = collect_future_flags(tree)
    findings: List[Finding] = []
    findings.extend(detect_future_imports(tree))
    findings.extend(detect_print_statements(tree))
    findings.extend(detect_old_except(tree))
    findings.extend(detect_old_raise(tree))
    findings.extend(detect_tuple_params(tree))
    findings.extend(detect_exec_statement(tree))
    findings.extend(detect_backtick_repr(tree))
    findings.extend(detect_old_octal(tree))
    findings.extend(detect_long_literal(tree))
    findings.extend(detect_integer_division(tree, future_flags))
    findings.extend(detect_dict_methods_and_builtins(tree))
    findings.extend(detect_removed_builtin_names(tree))
    findings.extend(detect_stdlib_renames(tree))
    findings.extend(detect_iter_builtin_misuse(tree))
    findings.extend(detect_dict_view_misuse(tree))
    findings.extend(detect_sorted_cmp_kwarg(tree))
    findings.extend(detect_ne_operator(source))
    findings.sort(key=lambda f: (f.line, f.column, f.construct_type))
    return findings, future_flags
