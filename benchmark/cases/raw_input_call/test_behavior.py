"""Behavioral oracle for raw_input_call."""
from unittest.mock import patch
from source_py2 import prompt_for_string, prompt_for_int, confirm


def test_prompt_for_string_strips():
    with patch('builtins.input', return_value='  hello  '):
        assert prompt_for_string('name: ') == 'hello'


def test_prompt_for_int_value():
    with patch('builtins.input', return_value='42'):
        assert prompt_for_int('num: ') == 42


def test_prompt_for_int_default():
    with patch('builtins.input', return_value=''):
        assert prompt_for_int('num: ', default=7) == 7


def test_confirm_yes():
    with patch('builtins.input', return_value='y'):
        assert confirm('proceed?') is True


def test_confirm_yes_full():
    with patch('builtins.input', return_value='yes'):
        assert confirm('proceed?') is True


def test_confirm_no():
    with patch('builtins.input', return_value='n'):
        assert confirm('proceed?') is False
