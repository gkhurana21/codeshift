"""Task scheduling with priority ordering."""


class Task(object):
    def __init__(self, name, priority):
        self.name = name
        self.priority = priority

    def __repr__(self):
        return 'Task({!r}, {})'.format(self.name, self.priority)

    def __cmp__(self, other):
        return cmp(self.priority, other.priority)


def task_cmp(a, b):
    return cmp(a.priority, b.priority)


def rank(tasks):
    return sorted(tasks, cmp=task_cmp)


def highest_priority(tasks):
    return sorted(tasks)[-1]


def lowest_priority(tasks):
    return sorted(tasks)[0]
