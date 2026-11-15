import time


def slow_result(output, payload_bytes):
    try:
        time.sleep(60)
    finally:
        output.close()


def oversized_result(output, payload_bytes):
    try:
        output.send_bytes(b"x" * (4 * 1024 * 1024 + 1))
    finally:
        output.close()


def abruptly_exit(output, payload_bytes):
    output.close()


def partial_frame(output, payload_bytes):
    import os
    import struct

    try:
        os.write(output.fileno(), struct.pack("!i", 1024) + b"{")
        time.sleep(60)
    finally:
        output.close()


def result_then_delayed_exit(output, payload_bytes, *, delay=3, ready=None, exit_code=0):
    import os
    from multiprocessing.util import Finalize

    Finalize(None, time.sleep, args=(delay,), exitpriority=0)
    output.send_bytes(b"completed-synthetic-result")
    output.close()
    if ready is not None:
        ready.set()
    if exit_code:
        os._exit(exit_code)
