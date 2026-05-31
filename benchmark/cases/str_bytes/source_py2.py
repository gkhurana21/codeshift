"""Byte-level string operations.

In Python 2, str IS bytes. Iterating over a str yields single-character str
objects; ord(c) converts them to integer byte values and chr(n) converts back.

In Python 3, bytes iteration yields int directly; chr() returns a unicode
character, not a byte. The migration must replace the ord/chr idiom with
direct integer arithmetic on bytes objects.
"""


def xor_bytes(a, b):
    """XOR two equal-length byte strings element by element.

    Py2: a, b are str (bytes); iterating yields single-char str;
    ord(c) needed to get the integer value; chr() to convert back.
    Returns str (bytes) in Py2; the Py3 migration must return bytes.
    """
    if len(a) != len(b):
        raise ValueError("inputs must have equal length: %d vs %d" % (len(a), len(b)))
    return ''.join(chr(ord(x) ^ ord(y)) for x, y in zip(a, b))


def bytes_to_hex(data):
    """Encode a byte string to lowercase hex.

    Py2: ord(c) for c in str gives each byte's integer value.
    """
    return ''.join('%02x' % ord(c) for c in data)


def hex_to_bytes(hexstr):
    """Decode a hex string back to bytes (str in Py2).

    Py2: chr(n) gives a single-char str for byte value n.
    """
    if len(hexstr) % 2 != 0:
        raise ValueError("hex string must have even length")
    return ''.join(chr(int(hexstr[i:i + 2], 16)) for i in range(0, len(hexstr), 2))


def byte_sum(data):
    """Sum all byte values in data.

    Py2: ord(c) needed since iterating str gives single-char str, not int.
    """
    return sum(ord(c) for c in data)
