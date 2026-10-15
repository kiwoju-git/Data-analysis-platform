import errno
import socket
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.core.config import Settings
from app.core.trusted_lan import (
    TrustedLanMiddleware,
    local_linux_ipv4_addresses,
    request_rejection,
)

HOSTS = frozenset({"127.0.0.1", "localhost", "192.168.40.12"})
AUTHORITY = "192.168.40.12:8600"
ORIGIN = "http://" + AUTHORITY


def rejection(headers, method="GET", port=8600):
    return request_rejection(
        {
            "type": "http",
            "method": method,
            "headers": [(name.encode("ascii"), value.encode("ascii")) for name, value in headers],
        },
        HOSTS,
        port,
    )


@pytest.mark.parametrize("host", [AUTHORITY, "127.0.0.1:8600", "localhost:8600"])
@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
def test_safe_methods_accept_only_admitted_host_without_origin(host, method):
    assert rejection([("host", host)], method) is None


@pytest.mark.parametrize(
    "host",
    [
        "evil.example:8600",
        "192.168.40.13:8600",
        "192.168.40.12",
        "192.168.40.12:8000",
        "192.168.40.12:65536",
        "192.168.40.12:not-a-port",
        "192.168.40.12:8600:8600",
        "0.0.0.0:8600",
        "localhost.evil.example:8600",
        "localhost.:8600",
        "user@192.168.40.12:8600",
        "192.168.40.12:8600/path",
        "192.168.40.12:8600?query",
        "192.168.40.12:8600#fragment",
        "192.168.40.12:8600\\evil",
        "192.168.40.12:8600,evil.example",
        "192.168.40.12:8600 ",
        "%31%39%32.168.40.12:8600",
        "[::1]:8600",
        "",
    ],
)
def test_host_authority_rejects_unlisted_malformed_and_ambiguous_values(host):
    assert rejection([("host", host)]) == "release_host_not_allowed"


def test_missing_and_duplicate_host_headers_are_rejected():
    assert rejection([]) == "release_host_not_allowed"
    assert rejection([("host", AUTHORITY), ("host", AUTHORITY)]) == "release_host_not_allowed"


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "TRACE"])
def test_unsafe_methods_require_exact_same_origin(method):
    assert rejection([("host", AUTHORITY)], method) == "release_origin_not_allowed"
    assert rejection([("host", AUTHORITY), ("origin", ORIGIN)], method) is None


@pytest.mark.parametrize(
    "origin",
    [
        "https://192.168.40.12:8600",
        "http://192.168.40.12",
        "http://192.168.40.12:8000",
        "http://127.0.0.1:8600",
        "http://localhost:8600",
        "http://192.168.40.13:8600",
        "http://192.168.40.12:8600/",
        "http://192.168.40.12:8600.evil.example",
        "null",
        "",
    ],
)
@pytest.mark.parametrize("method", ["GET", "POST", "OPTIONS"])
def test_any_present_origin_must_match_host_scheme_and_port(origin, method):
    headers = [("host", AUTHORITY), ("origin", origin)]
    assert rejection(headers, method) == "release_origin_not_allowed"


def test_duplicate_origin_and_cross_site_fetch_are_rejected():
    headers = [("host", AUTHORITY), ("origin", ORIGIN)]
    assert rejection([*headers, ("origin", ORIGIN)]) == "release_origin_not_allowed"
    assert rejection([*headers, ("sec-fetch-site", "cross-site")]) == "release_origin_not_allowed"
    assert rejection([*headers, ("sec-fetch-site", "same-origin")], "POST") is None
    assert (
        rejection([("host", AUTHORITY), ("sec-fetch-site", "same-site")], "POST")
        == "release_origin_not_allowed"
    )


def test_forwarded_headers_cannot_override_host_origin_or_scheme():
    spoof = [
        ("forwarded", f"host={AUTHORITY};proto=http;for=127.0.0.1"),
        ("x-forwarded-host", AUTHORITY),
        ("x-forwarded-proto", "http"),
        ("x-forwarded-for", "127.0.0.1"),
    ]
    assert rejection([("host", "evil.example:8600"), *spoof]) == "release_host_not_allowed"
    assert (
        rejection([("host", AUTHORITY), ("origin", "https://evil.example"), *spoof], "POST")
        == "release_origin_not_allowed"
    )
    assert rejection([("host", AUTHORITY), *spoof], "POST") == "release_origin_not_allowed"
    assert rejection([("host", AUTHORITY), ("origin", ORIGIN), *spoof], "POST") is None


async def allowed_endpoint(request):
    return JSONResponse({"allowed": True})


def test_middleware_errors_are_structured_redacted_and_do_not_echo_headers():
    app = Starlette(routes=[Route("/", allowed_endpoint, methods=["GET", "POST"])])
    app.add_middleware(TrustedLanMiddleware, hosts=["192.168.40.12"], port=8600)
    client = TestClient(app, base_url=ORIGIN)
    assert client.post("/", headers={"Origin": ORIGIN}).json() == {"allowed": True}
    for headers, expected_status, code in [
        ({"Host": "private-marker.evil:8600"}, 400, "release_host_not_allowed"),
        ({"Origin": "https://private-marker.evil"}, 403, "release_origin_not_allowed"),
        ({}, 403, "release_origin_not_allowed"),
    ]:
        response = client.post("/", headers=headers)
        assert response.status_code == expected_status
        assert response.json()["error"]["code"] == code
        assert UUID(response.json()["error"]["correlation_id"])
        assert response.json()["error"]["developer_detail"] is None
        assert "private-marker" not in response.text
        assert "access-control-allow-origin" not in response.headers


def lan_settings(tmp_path: Path, **overrides):
    web = tmp_path / "web"
    web.mkdir(exist_ok=True)
    (web / "index.html").write_text("<html>fixture</html>", encoding="utf-8")
    values = {
        "workspace_root": tmp_path / "workspace",
        "frontend_dist": web,
        "environment": "production",
        "bind_host": "0.0.0.0",
        "bind_port": 8600,
        "trusted_lan": True,
        "trusted_lan_hosts": ["192.168.40.12"],
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    "overrides",
    [
        {"environment": "development"},
        {"frontend_dist": None},
        {"bind_host": "127.0.0.1"},
        {"bind_host": "localhost"},
        {"bind_host": "192.168.40.12"},
        {"trusted_lan": False},
        {"trusted_lan": False, "bind_host": "127.0.0.1"},
        {"trusted_lan_hosts": ["192.168.40.12", "192.168.40.12"]},
        {"trusted_lan_hosts": ["127.0.0.1"]},
        {"trusted_lan_hosts": ["0.0.0.0"]},
        {"trusted_lan_hosts": ["224.0.0.1"]},
        {"trusted_lan_hosts": ["::1"]},
        {"trusted_lan_hosts": ["*.example"]},
        {"trusted_lan_hosts": ["192.168.40.12:8600"]},
    ],
)
def test_lan_settings_require_explicit_release_mode_and_valid_unique_hosts(tmp_path, overrides):
    with pytest.raises(ValidationError):
        lan_settings(tmp_path, **overrides)


def test_local_api_default_is_unchanged_and_empty_discovery_does_not_widen_hosts(tmp_path):
    settings = Settings(_env_file=None, workspace_root=tmp_path / "workspace")
    assert settings.bind_host == "127.0.0.1"
    assert settings.trusted_lan is False
    assert settings.trusted_lan_hosts == []
    assert "*" not in settings.cors_allowed_origins
    assert lan_settings(tmp_path, trusted_lan_hosts=[]).trusted_lan
    assert not (tmp_path / "workspace").exists()


def test_release_guard_wraps_cors_preflight_and_static_ui(tmp_path):
    from app.main import create_app

    app = create_app(lan_settings(tmp_path))
    client = TestClient(app, base_url=ORIGIN)
    assert client.get("/home").status_code == 200
    assert client.get("/api/v1/runtime-info").status_code == 200
    response = client.options(
        "/api/v1/datasets/paste",
        headers={
            "Origin": "http://127.0.0.1:8600",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "release_origin_not_allowed"
    assert "access-control-allow-origin" not in response.headers
    assert client.get("/home", headers={"Host": "evil.example:8600"}).status_code == 400


def fake_interface_discovery(monkeypatch, addresses):
    import app.core.trusted_lan as module

    monkeypatch.setattr(module.sys, "platform", "linux")
    names = list(addresses)
    monkeypatch.setattr(module.socket, "if_nameindex", lambda: list(enumerate(names, 1)))

    class Probe:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def fileno(self):
            return 42

    def ioctl(descriptor, operation, interface):
        assert descriptor == 42
        assert operation == 0x8915
        name = interface.split(b"\0", 1)[0].decode("utf-8")
        address = addresses[name]
        if isinstance(address, OSError):
            raise address
        return bytes(20) + socket.inet_aton(address) + bytes(8)

    def no_network(*args, **kwargs):
        raise AssertionError("Interface discovery must not perform DNS or outbound traffic")

    monkeypatch.setattr(module.socket, "socket", lambda *args: Probe())
    monkeypatch.setattr(module.socket, "getaddrinfo", no_network)
    monkeypatch.setattr(module.socket, "gethostbyname", no_network)
    monkeypatch.setitem(sys.modules, "fcntl", SimpleNamespace(ioctl=ioctl))


def test_linux_discovery_deduplicates_sorts_and_excludes_non_lan_addresses(monkeypatch):
    fake_interface_discovery(
        monkeypatch,
        {
            "eth0": "192.168.40.12",
            "eth1": "10.2.0.9",
            "alias": "192.168.40.12",
            "lo": "127.0.0.1",
            "unspecified": "0.0.0.0",
            "multicast": "224.0.0.1",
            "no-ipv4": OSError(errno.EADDRNOTAVAIL, "no IPv4"),
            "removed": OSError(errno.ENODEV, "interface disappeared"),
        },
    )
    assert local_linux_ipv4_addresses() == ["10.2.0.9", "192.168.40.12"]


def test_linux_discovery_propagates_unexpected_os_failure(monkeypatch):
    fake_interface_discovery(monkeypatch, {"eth0": OSError(errno.EPERM, "not permitted")})
    with pytest.raises(OSError) as failure:
        local_linux_ipv4_addresses()
    assert failure.value.errno == errno.EPERM


def test_linux_discovery_can_return_no_external_address(monkeypatch):
    fake_interface_discovery(monkeypatch, {"lo": "127.0.0.1"})
    assert local_linux_ipv4_addresses() == []


def test_discovery_does_not_pretend_to_support_windows(monkeypatch):
    import app.core.trusted_lan as module

    monkeypatch.setattr(module.sys, "platform", "win32")
    with pytest.raises(ValueError, match="requires Linux"):
        local_linux_ipv4_addresses()
