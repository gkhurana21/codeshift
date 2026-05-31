"""String template rendering and text transformation utilities."""
from __future__ import unicode_literals
import re


def render(template, context):
    for key, value in context.items():
        if not isinstance(value, unicode):
            value = unicode(value)
        template = template.replace(u'{' + key + u'}', value)
    return template


def slugify(text):
    if isinstance(text, unicode):
        text = text.lower()
    else:
        text = unicode(text).lower()
    return re.sub(u'[^a-z0-9]+', u'-', text).strip(u'-')


def truncate(text, max_len):
    if not isinstance(text, unicode):
        text = unicode(text)
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + u'...'
