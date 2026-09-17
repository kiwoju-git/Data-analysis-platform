"""Isolated dev.ps1 LAN/proxy and grouped-menu checks; no user workspace access."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from playwright.sync_api import expect, sync_playwright

from critical_path import terminate_process


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("0.0.0.0", 0))
        return int(probe.getsockname()[1])


def http_status(url: str, *, method: str = "GET", headers=None) -> int:
    try:
        with build_opener(ProxyHandler({})).open(
            Request(url, method=method, headers=headers or {}), timeout=3
        ) as response:
            return response.status
    except HTTPError as error:
        return error.code


def verify_menu(url: str, root: Path) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for locale in ("ko", "en"):
                context = browser.new_context()
                context.add_init_script(
                    f"localStorage.setItem('statistical-twin.locale', '{locale}')"
                )
                page = context.new_page()
                api_urls = []
                failures = []
                page.on("pageerror", lambda error: failures.append(str(error)))
                page.on(
                    "request",
                    lambda request: api_urls.append(request.url)
                    if "/api/v1/" in request.url
                    else None,
                )
                route = url + "/analysis?domain=mean-equivalence"
                for width, height in (
                    (1440, 900),
                    (1280, 800),
                    (1024, 768),
                    (390, 844),
                ):
                    page.set_viewport_size({"width": width, "height": height})
                    page.goto(route, wait_until="networkidle")
                    expect(page.locator(".runtime-mismatch-panel")).to_have_count(0)
                    groups = page.locator(".analysis-method-group")
                    expect(groups).to_have_count(4)
                    for group, count in zip(groups.all(), (3, 1, 3, 3)):
                        expect(group.locator("h3")).to_be_visible()
                        expect(
                            group.locator("button.analysis-domain-method-card")
                        ).to_have_count(count)
                        for card in group.locator("button").all():
                            assert card.evaluate(
                                "e => e.scrollWidth <= e.clientWidth + 1"
                            )
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= innerWidth + 1"
                    )
                    guide = page.locator(".analysis-domain-guide")
                    expect(guide).not_to_have_attribute("open", "")
                    guide.locator("summary").focus()
                    page.keyboard.press("Enter")
                    expect(guide).to_have_attribute("open", "")
                    page.keyboard.press("Enter")
                    first = groups.first.locator("button").first
                    first.focus()
                    assert (
                        first.evaluate("e => getComputedStyle(e).outlineStyle")
                        != "none"
                    )
                    page.keyboard.press("Enter")
                    expect(page).to_have_url(
                        url + "/analysis/hypothesis/hypothesis.one_sample_t"
                    )
                    page.go_back(wait_until="networkidle")
                    expect(page.locator(".analysis-method-group")).to_have_count(4)
                    page.reload(wait_until="networkidle")
                    expect(page.locator(".analysis-method-group")).to_have_count(4)
                    page.evaluate("scrollTo(0, 0)")
                    page.screenshot(
                        path=str(root / f"mean-groups-{locale}-{width}.png"),
                        full_page=True,
                    )

                page.set_viewport_size({"width": 1440, "height": 900})
                for index in range(10):
                    page.goto(route, wait_until="networkidle")
                    card = page.locator(".analysis-method-group button").nth(index)
                    name = card.get_attribute("aria-label")
                    card.click()
                    expect(page.locator("#workbench-title")).to_have_text(name)
                    assert "/analysis/hypothesis/hypothesis." in page.url
                # A same-origin mutation must reach the API (validation error, not proxy rejection).
                status = page.evaluate("""async () => (await fetch('/api/v1/datasets/paste', {
                    method: 'POST', headers: {'Content-Type':'application/json'}, body:'{}'
                })).status""")
                assert status == 422, status
                assert api_urls and all(
                    value.startswith(url + "/api/v1/") for value in api_urls
                )
                assert not failures, failures
                context.close()
        finally:
            browser.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lan-host", required=True, help="This host's actual LAN IPv4 address"
    )
    parser.add_argument("--diagnostics", type=Path, required=True)
    args = parser.parse_args()
    args.diagnostics.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[2]
    backend_port, frontend_port = free_port(), free_port()
    while backend_port == frontend_port:
        frontend_port = free_port()
    environment = os.environ.copy()
    results = []
    with tempfile.TemporaryDirectory(prefix="datalab-lan-test-") as temporary:
        environment["DATALAB_WORKSPACE_ROOT"] = str(Path(temporary) / "workspace")
        for local_only in (False, True):
            with (args.diagnostics / f"dev-local-{local_only}.log").open("wb") as log:
                command = [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(repo / "scripts/dev.ps1"),
                    "-BackendPort",
                    str(backend_port),
                    "-FrontendPort",
                    str(frontend_port),
                    "-StartupTimeoutSeconds",
                    "90",
                ]
                if local_only:
                    command.append("-LocalOnly")
                process = subprocess.Popen(
                    command,
                    cwd=repo,
                    env=environment,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                try:
                    local_url = f"http://127.0.0.1:{frontend_port}"
                    lan_url = f"http://{args.lan_host}:{frontend_port}"
                    deadline = time.monotonic() + 100
                    while True:
                        assert (
                            process.poll() is None
                        ), "dev.ps1 exited; inspect its diagnostic log"
                        try:
                            if http_status(local_url + "/api/v1/runtime-info") == 200:
                                break
                        except (URLError, TimeoutError):
                            pass
                        assert time.monotonic() < deadline, "dev.ps1 readiness timeout"
                        time.sleep(0.5)
                    if local_only:
                        try:
                            http_status(lan_url)
                        except (URLError, TimeoutError):
                            pass
                        else:
                            raise AssertionError(
                                "LocalOnly exposed the frontend on LAN"
                            )
                        results.append(
                            "LocalOnly: loopback works, LAN connection refused"
                        )
                    else:
                        assert http_status(lan_url + "/api/v1/runtime-info") == 200
                        assert (
                            http_status(lan_url, headers={"Host": "attacker.invalid"})
                            == 403
                        )
                        assert (
                            http_status(
                                lan_url + "/api/v1/runtime-info",
                                headers={"Origin": "https://attacker.invalid"},
                            )
                            == 403
                        )
                        assert (
                            http_status(
                                lan_url + "/api/v1/datasets/paste", method="POST"
                            )
                            == 403
                        )
                        verify_menu(lan_url, args.diagnostics)
                        results.append(
                            "LAN IPv4: runtime/API proxy, same-origin mutation, hostile Host/Origin rejection, KOR/ENG, 4 viewports, 10 routes passed"
                        )
                finally:
                    terminate_process(process)
            time.sleep(1)
    (args.diagnostics / "results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print("\n".join(results))


if __name__ == "__main__":
    main()
