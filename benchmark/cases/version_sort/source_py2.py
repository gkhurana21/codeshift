"""Semantic version comparison and ordering utilities."""


class Version(object):
    def __init__(self, major, minor, patch=0):
        self.major = major
        self.minor = minor
        self.patch = patch

    def __repr__(self):
        return '{}.{}.{}'.format(self.major, self.minor, self.patch)

    def __cmp__(self, other):
        return (cmp(self.major, other.major) or
                cmp(self.minor, other.minor) or
                cmp(self.patch, other.patch))


def sort_versions(versions):
    return sorted(versions, cmp=lambda a, b: (
        cmp(a.major, b.major) or cmp(a.minor, b.minor) or cmp(a.patch, b.patch)
    ))


def latest(versions):
    return sorted(versions)[-1]


def compare(a, b):
    return (cmp(a.major, b.major) or
            cmp(a.minor, b.minor) or
            cmp(a.patch, b.patch))
