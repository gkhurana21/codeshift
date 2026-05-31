# A deliberately gnarly Python 2 file. Exercises every detector in Phase 1.
# This file is INTENTIONALLY invalid Python 3.

from __future__ import absolute_import

import urllib
import urllib2
from StringIO import StringIO
import ConfigParser

print 'hello world'
print('this is the function form, do not flag')

# Old-style except + raise
try:
    x = 5 / 2
    n = len(map(int, ['1', '2', '3']))
    first = filter(None, ['a', '', 'b'])[0]
except IOError, e:
    print e
    raise IOError, 'bad'

# Old comparison operator
if 1 <> 2:
    pass

# Backtick repr + exec statement
y = `123`
exec 'z = 1'

# Tuple-unpacking parameter
def pair_sum((a, b)):
    return a + b

# Old octal + long literal
mode = 0755
big = 10L

# Dict iteration + has_key + .next() + iteritems + view indexing
d = {'a': 1, 'b': 2}
for k in d.iterkeys():
    print k
for k, v in d.iteritems():
    print k, v
if d.has_key('a'):
    print 'yes'
first_key = d.keys()[0]            # Py3: dict_keys is not subscriptable
nkeys = len(d.values())            # Py3: view object (works, but flagged)
it = iter(d)
first = it.next()

# Removed builtins
xs = xrange(10)
s = unicode('hi')
if isinstance(s, basestring):
    print 'string'
if isinstance(big, long):
    print 'long'
ans = raw_input('? ')
total = reduce(lambda a, b: a + b, xs)
ranked = sorted(['b', 'a'], cmp=lambda a, b: -1 if a < b else 1)

# Integer division with variables (heuristic flag)
def avg(a, b):
    return (a + b) / 2
