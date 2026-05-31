"""Unix file permission utilities."""

DEFAULT_FILE_PERMS = 0644
DEFAULT_DIR_PERMS = 0755
EXEC_PERMS = 0755
READ_ONLY = 0444


def make_writable(perms):
    return perms | 0200


def make_executable(perms):
    return perms | 0111


def perms_to_str(perms):
    result = ''
    for shift in [6, 3, 0]:
        bits = (perms >> shift) & 0007
        result += 'r' if bits & 4 else '-'
        result += 'w' if bits & 2 else '-'
        result += 'x' if bits & 1 else '-'
    return result
