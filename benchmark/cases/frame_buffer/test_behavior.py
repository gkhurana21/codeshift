"""Behavioral oracle for frame_buffer."""
from source_py2 import find_end, split_frames, join_chunks


def test_find_end_present():
    assert find_end(b'FRAME\r\n\r\nREST') == 5


def test_find_end_absent():
    assert find_end(b'incomplete') == -1


def test_split_frames_two():
    frames, remainder = split_frames(b'A\r\n\r\nB\r\n\r\nC')
    assert frames == [b'A', b'B']
    assert remainder == b'C'


def test_split_frames_none():
    frames, remainder = split_frames(b'incomplete')
    assert frames == []
    assert remainder == b'incomplete'


def test_split_frames_one():
    frames, remainder = split_frames(b'FIRST\r\n\r\n')
    assert frames == [b'FIRST']
    assert remainder == b''


def test_join_chunks():
    assert join_chunks([b'hello', b' ', b'world']) == b'hello world'


def test_join_chunks_empty():
    assert join_chunks([]) == b''
