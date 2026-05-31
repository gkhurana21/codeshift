"""Lookup tables used by the detectors."""

from __future__ import annotations

# Dict-iteration / membership methods removed in Py3.
DICT_PY2_METHODS = {
    "iteritems": "items",
    "itervalues": "values",
    "iterkeys": "keys",
    "has_key": "in operator",
}

# Removed Py2 builtins (used by name).
REMOVED_BUILTIN_NAMES = {
    "xrange": "range",
    "unicode": "str",
    "basestring": "str",
    "unichr": "chr",
    "long": "int",
    "cmp": "(removed - define your own comparator)",
    "apply": "(removed - call f(*args, **kwargs) directly)",
    "reload": "importlib.reload",
    "reduce": "functools.reduce",
    "raw_input": "input",
}

# Stdlib module renames / reorganizations for `import X` and `from X import Y`.
# Maps Py2 top-level module name -> Py3 replacement hint.
STDLIB_RENAMES = {
    "urllib2": "urllib.request / urllib.error",
    "urlparse": "urllib.parse",
    "urllib": "urllib.parse / urllib.request (split)",
    "StringIO": "io.StringIO",
    "cStringIO": "io.BytesIO / io.StringIO",
    "ConfigParser": "configparser",
    "Queue": "queue",
    "cPickle": "pickle",
    "SocketServer": "socketserver",
    "BaseHTTPServer": "http.server",
    "SimpleHTTPServer": "http.server",
    "CGIHTTPServer": "http.server",
    "Cookie": "http.cookies",
    "cookielib": "http.cookiejar",
    "htmlentitydefs": "html.entities",
    "HTMLParser": "html.parser",
    "xmlrpclib": "xmlrpc.client",
    "DocXMLRPCServer": "xmlrpc.server",
    "SimpleXMLRPCServer": "xmlrpc.server",
    "__builtin__": "builtins",
    "copy_reg": "copyreg",
    "Tkinter": "tkinter",
    "tkFileDialog": "tkinter.filedialog",
    "tkMessageBox": "tkinter.messagebox",
    "thread": "_thread",
    "dummy_thread": "_dummy_thread",
}

# __future__ features the analyzer cares about for neutralization logic.
FUTURE_NEUTRALIZES_INT_DIV = "division"
