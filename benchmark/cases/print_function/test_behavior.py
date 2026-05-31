"""Behavioral oracle for print_function."""
from source_py2 import log_message, log_values, debug_dump


def test_log_message(capsys):
    log_message('hello')
    assert capsys.readouterr().out.strip() == 'hello'


def test_log_values(capsys):
    log_values('nums', 1, 2, 3)
    assert capsys.readouterr().out.strip() == 'nums: 1, 2, 3'


def test_log_values_single(capsys):
    log_values('x', 42)
    assert capsys.readouterr().out.strip() == 'x: 42'


def test_debug_dump_contains_keys(capsys):
    debug_dump('test', {'x': 1, 'y': 2})
    out = capsys.readouterr().out
    assert 'x' in out
    assert 'y' in out
    assert '1' in out
    assert '2' in out


def test_debug_dump_has_title(capsys):
    debug_dump('MyTitle', {})
    out = capsys.readouterr().out
    assert 'MyTitle' in out
