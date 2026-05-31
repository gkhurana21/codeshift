"""Behavioral oracle for priority_task."""
from source_py2 import Task, rank, highest_priority, lowest_priority, task_cmp


def test_rank_order():
    tasks = [Task('c', 3), Task('a', 1), Task('b', 2)]
    result = rank(tasks)
    assert [t.name for t in result] == ['a', 'b', 'c']


def test_highest_priority():
    tasks = [Task('x', 5), Task('y', 1), Task('z', 3)]
    assert highest_priority(tasks).name == 'x'


def test_lowest_priority():
    tasks = [Task('x', 5), Task('y', 1), Task('z', 3)]
    assert lowest_priority(tasks).name == 'y'


def test_task_cmp_less_than():
    assert task_cmp(Task('a', 1), Task('b', 2)) < 0


def test_task_cmp_equal():
    assert task_cmp(Task('a', 1), Task('b', 1)) == 0


def test_task_cmp_greater_than():
    assert task_cmp(Task('a', 5), Task('b', 2)) > 0
