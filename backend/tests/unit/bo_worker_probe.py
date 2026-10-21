"""Small spawn targets isolate BO pipe/timeout tests from application imports."""

import json
import time


def large_result(send, payload):
    message = {"status": "ok", "result": {"fixture": "x" * 500_000}}
    send.send_bytes(json.dumps(message).encode("utf-8"))
    send.close()


def slow_result(send, payload):
    time.sleep(60)
