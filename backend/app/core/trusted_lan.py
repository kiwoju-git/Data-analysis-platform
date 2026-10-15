"""Browser-origin defenses for the owner-approved, shared Linux LAN release."""

import errno
import ipaddress
import re
import socket
import struct
import sys
from urllib.parse import urlsplit
from uuid import uuid4

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.errors import error_response


def local_linux_ipv4_addresses() -> list[str]:
    """Read assigned interface addresses without DNS, external traffic or subprocesses."""
    if sys.platform != "linux":
        raise ValueError("LAN release address discovery requires Linux")
    import fcntl

    addresses: set[str] = set()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        for _, name in socket.if_nameindex():
            try:
                interface = fcntl.ioctl(
                    probe.fileno(), 0x8915, struct.pack("256s", name.encode("utf-8"))
                )
            except OSError as error:
                if error.errno in {errno.EADDRNOTAVAIL, errno.ENODEV}:
                    continue
                raise
            address = ipaddress.IPv4Address(interface[20:24])
            if not (address.is_loopback or address.is_unspecified or address.is_multicast):
                addresses.add(str(address))
    return sorted(addresses, key=ipaddress.IPv4Address)


def request_rejection(scope: Scope, hosts: frozenset[str], port: int) -> str | None:
    headers = Headers(scope=scope)
    host_values = headers.getlist("host")
    if len(host_values) != 1 or re.search(r"[\s/@\\?#%,\[\]]", host_values[0]):
        return "release_host_not_allowed"
    try:
        host = urlsplit("http://" + host_values[0])
        if host.hostname not in hosts or (host.port or 80) != port:
            return "release_host_not_allowed"
    except ValueError:
        return "release_host_not_allowed"
    expected_origin = f"http://{host.hostname}" + (f":{port}" if port != 80 else "")
    origins = headers.getlist("origin")
    if len(origins) > 1 or (origins and origins[0] != expected_origin):
        return "release_origin_not_allowed"
    if headers.get("sec-fetch-site") == "cross-site":
        return "release_origin_not_allowed"
    if scope.get("method", "GET") not in {"GET", "HEAD", "OPTIONS"} and origins != [
        expected_origin
    ]:
        return "release_origin_not_allowed"
    return None


class TrustedLanMiddleware:
    def __init__(self, app: ASGIApp, *, hosts: list[str], port: int) -> None:
        self.app = app
        self.hosts = frozenset(["127.0.0.1", "localhost", *hosts])
        self.port = port

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            code = request_rejection(scope, self.hosts, self.port)
            if code is not None:
                response = error_response(
                    code=code,
                    message="Use the server's displayed address and same-origin requests.",
                    correlation_id=str(uuid4()),
                    status_code=400 if code == "release_host_not_allowed" else 403,
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
