"""Console logging and output utilities."""
import sys


def log_message(msg):
    print msg


def log_error(msg):
    print >> sys.stderr, msg


def log_values(label, *values):
    print label + ':', ', '.join(str(v) for v in values)


def debug_dump(title, data):
    print '=== ' + title + ' ==='
    for key in sorted(data.keys()):
        print '  ' + str(key) + ': ' + str(data[key])
    print '==='
