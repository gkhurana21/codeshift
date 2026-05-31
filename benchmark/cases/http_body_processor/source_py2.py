"""HTTP response body processing utilities."""


def parse_content_length(header_block):
    for line in header_block.split('\r\n'):
        if line.lower().startswith('content-length:'):
            return int(line.split(':', 1)[1].strip())
    return 0


def strip_chunked_body(body):
    out = ''
    pos = 0
    while pos < len(body):
        crlf = body.index('\r\n', pos)
        size = int(body[pos:crlf], 16)
        if size == 0:
            break
        pos = crlf + 2
        out += body[pos:pos + size]
        pos += size + 2
    return out


def body_to_lines(body):
    return [ln for ln in body.split('\n') if ln.strip()]
