"""App readiness and child-page diagnostics for synthetic browser fixtures."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Iterator
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Browser, Page, expect


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
