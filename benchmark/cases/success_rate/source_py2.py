"""Campaign performance metrics."""


def hit_rate(hits, total):
    return hits * 100 / total


def miss_rate(hits, total):
    return (total - hits) * 100 / total


def improvement(before, after, base):
    return (after - before) * 100 / base
