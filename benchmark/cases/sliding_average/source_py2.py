"""Running statistics for a data stream."""


def running_mean(values):
    total = 0
    count = 0
    for v in values:
        total += v
        count += 1
    return total / count


def windowed_mean(values, window):
    subset = values[-window:]
    return sum(subset) / len(subset)


def quantize(value, step):
    return value / step * step
