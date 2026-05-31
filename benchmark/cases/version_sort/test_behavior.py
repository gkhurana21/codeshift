"""Behavioral oracle for version_sort."""
from source_py2 import Version, sort_versions, latest, compare


def test_sort_versions_ascending():
    vs = [Version(2, 0), Version(1, 9), Version(1, 10)]
    result = sort_versions(vs)
    assert [repr(v) for v in result] == ['1.9.0', '1.10.0', '2.0.0']


def test_sort_versions_patch():
    vs = [Version(1, 0, 3), Version(1, 0, 1), Version(1, 0, 2)]
    result = sort_versions(vs)
    assert [repr(v) for v in result] == ['1.0.1', '1.0.2', '1.0.3']


def test_latest():
    vs = [Version(1, 0), Version(2, 0), Version(1, 9)]
    assert repr(latest(vs)) == '2.0.0'


def test_compare_less_than():
    assert compare(Version(1, 0), Version(2, 0)) < 0


def test_compare_equal():
    assert compare(Version(1, 2, 3), Version(1, 2, 3)) == 0


def test_compare_greater_than():
    assert compare(Version(2, 0), Version(1, 9)) > 0


def test_compare_minor_dominates():
    assert compare(Version(1, 10), Version(1, 9)) > 0
