"""Behavioral oracle for octal_literal."""
from source_py2 import (DEFAULT_FILE_PERMS, DEFAULT_DIR_PERMS,
                         READ_ONLY, make_writable, make_executable, perms_to_str)


def test_default_file_perms():
    assert DEFAULT_FILE_PERMS == 0o644


def test_default_dir_perms():
    assert DEFAULT_DIR_PERMS == 0o755


def test_read_only():
    assert READ_ONLY == 0o444


def test_make_writable():
    assert make_writable(0o444) == 0o644


def test_make_executable():
    assert make_executable(0o644) == 0o755


def test_perms_to_str_644():
    assert perms_to_str(0o644) == 'rw-r--r--'


def test_perms_to_str_755():
    assert perms_to_str(0o755) == 'rwxr-xr-x'


def test_perms_to_str_444():
    assert perms_to_str(0o444) == 'r--r--r--'
