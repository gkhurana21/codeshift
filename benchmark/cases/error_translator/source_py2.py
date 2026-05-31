"""Configuration and input parsing with domain-error translation."""


class AppError(Exception):
    pass


def load_config(config_dict, key):
    try:
        return config_dict[key]
    except KeyError, e:
        raise AppError('missing config key: ' + str(e))


def parse_int(s):
    try:
        return int(s)
    except ValueError, e:
        raise AppError('invalid integer: ' + str(e))


def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError, e:
        raise AppError('division by zero')
