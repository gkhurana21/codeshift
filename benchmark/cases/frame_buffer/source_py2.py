"""Network frame buffering utilities."""

DELIMITER = '\r\n\r\n'


def find_end(buf):
    return buf.find(DELIMITER)


def split_frames(buf):
    frames = []
    while True:
        end = buf.find(DELIMITER)
        if end == -1:
            break
        frames.append(buf[:end])
        buf = buf[end + len(DELIMITER):]
    return frames, buf


def join_chunks(chunks):
    return ''.join(chunks)
