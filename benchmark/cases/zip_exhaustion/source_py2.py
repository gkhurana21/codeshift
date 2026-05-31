"""Multi-pass sequence combination utilities."""


def stats(keys, values):
    pairs = zip(keys, values)
    as_list = list(pairs)
    count = len(list(pairs))
    return as_list, count


def find_and_count(keys, values, target_key):
    pairs = zip(keys, values)
    target_val = None
    for k, v in pairs:
        if k == target_key:
            target_val = v
    remaining = list(pairs)
    return target_val, len(remaining)


def multi_pass(seq_a, seq_b):
    paired = zip(seq_a, seq_b)
    first_pass = [a + b for a, b in paired]
    second_pass = [a * b for a, b in paired]
    return first_pass, second_pass
