"""App readiness and child-page diagnostics for synthetic browser fixtures."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import traceback
from collections import Counter, deque
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Iterator
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Browser, ConsoleMessage, Page, Request, Response, expect


class SyntheticPageDiagnostics:
    """Observe an existing synthetic child page without changing its context."""

    def __init__(self, page: Page, root: Path, name: str) -> None:
        self.page = page
        self.target = root / name
        self.stage = name
        self.events: deque[dict[str, object]] = deque(maxlen=100)
        self.trace_started = False
        self.listeners = {
            "pageerror": self._page_error,
            "console": self._console,
            "requestfailed": self._request_failed,
            "request": self._request,
            "response": self._response,
        }

    def start(self) -> None:
        self.target.mkdir(parents=True, exist_ok=True)
        self.page.context.tracing.start(screenshots=True, snapshots=True, sources=False)
        self.trace_started = True
        for event, listener in self.listeners.items():
            self.page.on(event, listener)

    def _record(self, kind: str, **fields: object) -> None:
        self.events.append({"kind": kind, "stage": self.stage, **fields})

    def _page_error(self, error: object) -> None:
        self._record("pageerror", message=str(error)[:1000])

    def _console(self, message: ConsoleMessage) -> None:
        if message.type in {"warning", "error"}:
            self._record("console", level=message.type, message=message.text[:1000])

    def _request_failed(self, request: Request) -> None:
        self._record(
            "requestfailed",
            method=request.method,
            path=urlsplit(request.url).path[:500],
            resource_type=request.resource_type,
            failure=str(request.failure)[:1000],
        )

    def _request(self, request: Request) -> None:
        path = urlsplit(request.url).path
        if path.startswith("/api/v1/regression-models/predictions/") and path.endswith(
            "/exports/csv"
        ):
            self._record("csv_export_request", method=request.method, path=path[:500])

    def _response(self, response: Response) -> None:
        path = urlsplit(response.url).path
        if path.startswith("/api/v1/regression-models/predictions/") and path.endswith(
            "/exports/csv"
        ):
            self._record(
                "csv_export_response",
                method=response.request.method,
                path=path[:500],
                status=response.status,
            )

    def capture_failure(self, failure: BaseException) -> None:
        failure.e2e_child_diagnostics = str(self.target)
        evidence: dict[str, object] = {
            "fixture": "synthetic",
            "stage": self.stage,
            "platform": platform.platform(),
            "python": platform.python_version(),
            "failure_type": type(failure).__name__,
            "events": list(self.events),
            "event_limit": self.events.maxlen,
        }
        try:
            evidence.update(source_identity())
        except Exception as diagnostic_error:
            evidence["source_capture_error"] = type(diagnostic_error).__name__
        captures = {
            "browser": lambda: self.page.context.browser.version,
            "socket_snapshot": socket_failure_diagnostics,
            "url": lambda: self.page.url,
            "viewport": lambda: self.page.viewport_size,
            "document": lambda: self.page.evaluate("""() => ({
                lang: document.documentElement.lang,
                appliedLocale: document.documentElement.dataset.appLocale ?? null,
                rootMounted: !!document.querySelector('#root > *'),
                runtime: document.querySelector('[data-runtime-state]')?.dataset.runtimeState ?? null,
                route: document.querySelector('.workspace')?.dataset.page ?? null
            })"""),
            "screenshot": lambda: self.page.screenshot(
                path=str(self.target / "failure.png"), full_page=True
            )
            and None,
            "dom": lambda: (self.target / "failure.html").write_text(
                self.page.content(), encoding="utf-8"
            ),
        }
        for key, capture in captures.items():
            try:
                evidence[key] = capture()
            except Exception as diagnostic_error:
                evidence[key + "_capture_error"] = type(diagnostic_error).__name__
        try:
            (self.target / "failure.json").write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as diagnostic_error:
            print(
                f"[diagnostics] Child capture failed: {type(diagnostic_error).__name__}",
                file=sys.stderr,
            )

    def finish(self, *, failed: bool) -> None:
        cleanup_errors: list[Exception] = []
        for event, listener in self.listeners.items():
            try:
                self.page.remove_listener(event, listener)
            except Exception as error:
                cleanup_errors.append(error)
        try:
            (self.target / "events.json").write_text(
                json.dumps(
                    {"fixture": "synthetic", "events": list(self.events)},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception as error:
            cleanup_errors.append(error)
        try:
            if self.trace_started:
                self.page.context.tracing.stop(path=str(self.target / "trace.zip"))
        except Exception as error:
            cleanup_errors.append(error)
        for error in cleanup_errors:
            print(
                f"[diagnostics] Child cleanup failed: {type(error).__name__}",
                file=sys.stderr,
            )
        if cleanup_errors and not failed:
            raise cleanup_errors[0]


def tcp_state_counts(output: str) -> dict[str, int]:
    """Retain only aggregate Windows TCP states, never socket addresses or PIDs."""
    states = {
        "CLOSED",
        "LISTENING",
        "SYN_SENT",
        "SYN_RECEIVED",
        "ESTABLISHED",
        "FIN_WAIT_1",
        "FIN_WAIT_2",
        "CLOSE_WAIT",
        "CLOSING",
        "LAST_ACK",
        "TIME_WAIT",
    }
    counts: Counter[str] = Counter()
    for line in output.splitlines():
        fields = line.split()
        if len(fields) == 4 and fields[0] == "TCP" and fields[-1] in states:
            counts[fields[-1]] += 1
    return dict(sorted(counts.items()))


def socket_failure_diagnostics() -> dict[str, object]:
    """A bounded, read-only failure snapshot, not proof of resource exhaustion."""
    if platform.system() != "Windows":
        return {"status": "not_collected", "reason": "windows_tcp_diagnostic_only"}
    try:
        result = subprocess.run(
            ["netstat.exe", "-an", "-p", "tcp"],
            capture_output=True,
            text=True,
            errors="replace",
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return {"status": "unavailable", "error_type": type(error).__name__}
    counts = tcp_state_counts(result.stdout)
    return {
        "status": "collected",
        "scope": "host_aggregate_not_browser_attribution",
        "tcp_states": counts,
        "total_tcp_sockets": sum(counts.values()),
    }


@lru_cache(maxsize=1)
def source_identity() -> dict[str, object]:
    root = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return {
            "source_commit": commit.stdout.strip(),
            "tracked_changes": bool(status.stdout),
        }
    except (OSError, subprocess.SubprocessError):
        return {"source_commit": None, "tracked_changes": None}


def wait_for_app_ready(
    page: Page, expected_locale: str, expected_route: str, *, timeout_ms: int = 15_000
) -> None:
    """Network inactivity, provider locale and a rendered route are distinct gates."""
    expect(page.locator("#root .app-shell")).to_be_visible(timeout=15_000)
    expect(page.locator(".app-shell")).to_have_attribute(
        "data-runtime-state", "compatible", timeout=15_000
    )
    expect(page.locator("html")).to_have_attribute("data-app-locale", expected_locale)
    expect(page.locator("html")).to_have_attribute("lang", expected_locale)
    path = urlsplit(expected_route).path
    expected_page = {
        "/": "home",
        "/home": "home",
        "/project": "home",
        "/datasets": "dataset",
        "/graphs": "graphs",
        "/reports": "reports",
        "/help": "help",
        "/manage": "manage",
    }.get(path, "analysis" if path.startswith("/analysis") else None)
    assert expected_page is not None, f"Unspecified readiness route: {expected_route}"
    workspace = page.locator(f'.workspace[data-page="{expected_page}"]')
    expect(workspace).to_be_visible()
    if path == "/analysis":
        domain = parse_qs(urlsplit(expected_route).query).get("domain", [None])[0]
        if domain is None:
            expect(workspace.locator(".analysis-domain-grid")).to_be_visible(
                timeout=timeout_ms
            )
        else:
            expect(workspace.locator(".analysis-domain-landing")).to_have_attribute(
                "data-domain-id", domain, timeout=timeout_ms
            )
            expect(workspace.locator(".analysis-domain-guide")).to_be_visible()
    if path.startswith("/analysis/"):
        expect(workspace.locator("#workbench-title")).to_be_visible(timeout=15_000)
    else:
        heading_id = workspace.get_attribute("aria-labelledby")
        assert heading_id
        expect(workspace.locator(f"#{heading_id}")).to_be_visible(timeout=15_000)
    expect(
        workspace.locator('.analysis-panel-load-state[role="status"]')
    ).to_have_count(0)
    expect(workspace.locator('.analysis-panel-load-state[role="alert"]')).to_have_count(
        0
    )
    actual = urlsplit(page.url)
    assert actual.path == path or (path in ("/", "/project") and actual.path == "/home")
    for query in urlsplit(expected_route).query.split("&"):
        if query:
            assert query in actual.query.split("&"), (expected_route, page.url)


def wait_for_bayesian_ready(
    page: Page, expected_locale: str, expected_route: str, *, timeout_ms: int = 15_000
) -> None:
    """The BO route's source catalog must finish before mutation controls are usable."""
    wait_for_app_ready(page, expected_locale, expected_route, timeout_ms=timeout_ms)
    catalog = page.locator('section[aria-labelledby="bayesian-study-catalog-title"]')
    expect(catalog).to_be_visible(timeout=timeout_ms)
    expect(catalog.get_by_role("status")).to_have_count(0, timeout=timeout_ms)
    expect(catalog.get_by_role("alert")).to_have_count(0, timeout=timeout_ms)


def wait_for_layout_settled(page: Page) -> None:
    """Wait for applied viewport styles and the real drawer transition, not a timer."""
    page.evaluate("""async () => {
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        const sidebar = document.querySelector('#application-sidebar');
        if (!sidebar) throw new Error('Application sidebar is not mounted');
        await Promise.allSettled(
            sidebar.getAnimations({subtree: true}).map(animation => animation.finished)
        );
        await new Promise(resolve => requestAnimationFrame(resolve));
    }""")


@contextmanager
def diagnosed_page(
    browser: Browser,
    root: Path,
    name: str,
    *,
    locale: str | None = None,
    init_script: str | None = None,
    allow_page_errors: bool = False,
) -> Iterator[Page]:
    """Own the actual tested context; always close it, including assertion failures."""
    target = root / name
    target.mkdir(parents=True, exist_ok=True)
    context = browser.new_context()
    page: Page | None = None
    trace_started = False
    original_failure: BaseException | None = None
    errors: list[str] = []
    failed_assets: list[dict[str, object]] = []
    try:
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        trace_started = True
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "requestfailed",
            lambda request: failed_assets.append(
                {"url": request.url, "failure": request.failure}
            )
            if request.resource_type in ("script", "stylesheet")
            else None,
        )
        page.on(
            "response",
            lambda response: failed_assets.append(
                {"url": response.url, "status": response.status}
            )
            if response.status >= 400
            and response.request.resource_type in ("script", "stylesheet")
            else None,
        )
        if locale is not None:
            context.add_init_script(
                "localStorage.setItem('statistical-twin.locale', "
                + json.dumps(locale)
                + ")"
            )
        if init_script is not None:
            context.add_init_script(init_script)
        yield page
        if not allow_page_errors:
            assert not errors, errors
    except BaseException as failure:
        original_failure = failure
        failure.e2e_child_diagnostics = str(target)
        evidence: dict[str, object] = {
            "fixture": "synthetic",
            "expected_locale": locale,
            "pageerrors": errors,
            "failed_assets": failed_assets,
            "platform": platform.platform(),
            "python": platform.python_version(),
            "browser": browser.version,
            "stage": name,
            "failure_type": type(failure).__name__,
            "socket_snapshot": socket_failure_diagnostics(),
            "failure_traceback": traceback.format_exception(
                type(failure), failure, failure.__traceback__
            ),
            **source_identity(),
        }
        # Diagnostics must not replace the original failure if the renderer crashed.
        if page is not None:
            captures = {
                "url": lambda: page.url,
                "viewport": lambda: page.viewport_size,
                "document": lambda: page.evaluate("""() => ({
                lang: document.documentElement.lang,
                appliedLocale: document.documentElement.dataset.appLocale ?? null,
                rootMounted: !!document.querySelector('#root > *'),
                runtime: document.querySelector('[data-runtime-state]')?.dataset.runtimeState ?? null,
                route: document.querySelector('.workspace')?.dataset.page ?? null
                })"""),
                "screenshot": lambda: page.screenshot(
                    path=str(target / "failure.png"), full_page=True
                )
                and None,
                "dom": lambda: (target / "failure.html").write_text(
                    page.content(), encoding="utf-8"
                ),
            }
            for key, capture in captures.items():
                try:
                    evidence[key] = capture()
                except Exception as diagnostic_error:
                    evidence[key + "_capture_error"] = type(diagnostic_error).__name__
        try:
            (target / "failure.json").write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as diagnostic_error:
            print(
                f"[diagnostics] JSON capture failed: {type(diagnostic_error).__name__}",
                file=sys.stderr,
            )
        raise
    finally:
        cleanup_errors: list[Exception] = []
        try:
            if trace_started:
                context.tracing.stop(path=str(target / "trace.zip"))
        except Exception as cleanup_error:
            cleanup_errors.append(cleanup_error)
        try:
            context.close()
        except Exception as cleanup_error:
            cleanup_errors.append(cleanup_error)
        for cleanup_error in cleanup_errors:
            print(
                f"[diagnostics] Cleanup failed: {type(cleanup_error).__name__}",
                file=sys.stderr,
            )
        if cleanup_errors and original_failure is None:
            raise cleanup_errors[0]
