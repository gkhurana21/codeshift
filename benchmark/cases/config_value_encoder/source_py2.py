"""Configuration value lookup and encoding for a settings store."""

DEFAULTS = {'timeout': '30', 'retries': '3', 'mode': 'fast'}


def get_value(config_bytes, key):
    for line in config_bytes.split('\n'):
        line = line.strip()
        if not line:
            continue
        if '=' in line:
            k, _, v = line.partition('=')
            if k.strip() == key:
                return v.strip()
    return None


def merge_defaults(config_bytes):
    result = {}
    for key, default in DEFAULTS.items():
        found = get_value(config_bytes, key)
        result[key] = found if found is not None else default
    return result


def encode_pair(key, value):
    return key + '=' + value + '\n'
