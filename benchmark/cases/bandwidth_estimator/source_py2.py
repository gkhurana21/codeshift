"""Network throughput calculations."""


def bytes_per_second(total_bytes, elapsed_ms):
    return total_bytes * 1000 / elapsed_ms


def bits_per_ms(total_bytes, elapsed_ms):
    return total_bytes * 8 / elapsed_ms


def eta_seconds(remaining_bytes, rate_bps):
    return remaining_bytes / rate_bps
