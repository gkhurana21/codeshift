"""Interactive prompt utilities."""


def prompt_for_string(message):
    return raw_input(message).strip()


def prompt_for_int(message, default=0):
    raw = raw_input(message).strip()
    if not raw:
        return default
    return int(raw)


def confirm(message):
    answer = raw_input(message + ' [y/n]: ').strip().lower()
    return answer in ('y', 'yes')
