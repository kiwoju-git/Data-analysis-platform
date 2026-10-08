import socket
import sys

import pytest

from app.core.network_ports import check_tcp_port_available


def test_port_probe_rejects_an_active_reusable_listener() -> None:
    with socket.socket() as listener:
        if sys.platform == "linux":
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        with pytest.raises(OSError):
            check_tcp_port_available("127.0.0.1", port)
    check_tcp_port_available("127.0.0.1", port)


@pytest.mark.skipif(sys.platform != "linux", reason="Linux TCP TIME_WAIT restart policy")
def test_linux_port_probe_allows_a_closed_connection_in_time_wait() -> None:
    with socket.socket() as listener, socket.socket() as client:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.settimeout(2)
        client.settimeout(2)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        client.connect(("127.0.0.1", port))
        connection, _ = listener.accept()
        with connection:
            connection.shutdown(socket.SHUT_WR)
            assert client.recv(1) == b""
    with socket.socket() as non_reusable_probe, pytest.raises(OSError):
        non_reusable_probe.bind(("127.0.0.1", port))
    check_tcp_port_available("127.0.0.1", port)
