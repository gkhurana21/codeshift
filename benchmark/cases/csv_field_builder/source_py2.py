"""Record serialization for a log-and-transmit pipeline."""

SEP = ','
NEWLINE = '\n'


def format_field(value):
    return str(value)


def format_record(fields):
    return SEP.join(format_field(f) for f in fields) + NEWLINE


def format_batch(records):
    return ''.join(format_record(row) for row in records)
