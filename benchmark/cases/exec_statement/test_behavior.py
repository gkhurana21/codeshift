"""Behavioral oracle for exec_statement."""
from source_py2 import eval_expression, run_snippet, define_function


def test_eval_expression_arithmetic():
    ctx = {}
    assert eval_expression('2 + 2', ctx) == 4


def test_eval_expression_uses_context():
    ctx = {'x': 10}
    assert eval_expression('x * 3', ctx) == 30


def test_run_snippet_assignment():
    ns = run_snippet('x = 42')
    assert ns['x'] == 42


def test_run_snippet_multiple_statements():
    ns = run_snippet('a = 1\nb = 2\nc = a + b')
    assert ns['c'] == 3


def test_define_function_simple():
    ns = {}
    f = define_function('add', ['a', 'b'], ['return a + b'], ns)
    assert f(3, 4) == 7


def test_define_function_with_condition():
    ns = {}
    f = define_function('clamp', ['x'], ['if x < 0: return 0', 'return x'], ns)
    assert f(-5) == 0
    assert f(3) == 3
