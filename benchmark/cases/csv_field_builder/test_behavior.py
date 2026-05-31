"""Behavioral oracle for csv_field_builder.

# NOTE: coin-flip-by-construction — oracle pins the bytes output path.
# A pass on this case is NOT evidence of F1 competence; it means the agent
# happened to pick the bytes interpretation over the equally-valid text
# interpretation. Both are defensible from the source alone.
"""
from source_py2 import format_record, format_batch


def test_format_record_strings():
    assert format_record(['x', '1']) == b'x,1\n'


def test_format_record_mixed_types():
    assert format_record([1, 2, 3]) == b'1,2,3\n'


def test_format_record_booleans():
    assert format_record([True, False]) == b'True,False\n'


def test_format_batch():
    assert format_batch([['a', 'b'], ['c', 'd']]) == b'a,b\nc,d\n'


def test_format_batch_single_row():
    assert format_batch([['only']]) == b'only\n'


def test_format_batch_empty():
    assert format_batch([]) == b''
