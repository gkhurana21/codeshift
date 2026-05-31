"""File I/O configuration handler."""


def read_config_lines(lines):
    config = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            key, _, value = line.partition('=')
            config[key.strip()] = value.strip()
    return config


def format_config(config_dict):
    parts = []
    for key, value in config_dict.iteritems():
        if isinstance(value, unicode):
            parts.append(key + '=' + value)
        elif isinstance(value, basestring):
            parts.append(key + '=' + value)
        else:
            parts.append(key + '=' + repr(value))
    return '\n'.join(sorted(parts))


def normalize_value(value):
    if isinstance(value, basestring):
        return value.strip()
    return value
