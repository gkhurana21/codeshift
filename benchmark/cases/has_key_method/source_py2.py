"""Dictionary lookup utilities."""


def safe_get(d, key, default=None):
    if d.has_key(key):
        return d[key]
    return default


def contains_all(d, keys):
    return all(d.has_key(k) for k in keys)


def merge_missing(base, updates):
    result = dict(base)
    for k, v in updates.items():
        if not result.has_key(k):
            result[k] = v
    return result
