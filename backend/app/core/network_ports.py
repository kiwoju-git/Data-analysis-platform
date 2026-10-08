import socket
import sys


def check_tcp_port_available(host: str, port: int) -> None:
    with socket.socket() as probe:
        if sys.platform == "linux":
            # Match Uvicorn's restart semantics without sharing an active listener.
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind((host, port))
