from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)
from playwright.sync_api import expect, sync_playwright


SAMPLE_DATA = """Group\tValue
A\t10
A\t11
A\t12
B\t15
B\t16
B\t17
"""

REGRESSION_SAMPLE_DATA = """adcc\tafucose\tgroup
5.2\t0\tA
7.9\t2\tA
11.3\t4\tA
13.8\t6\tA
8.3\t1\tB
11.6\t3\tB
14.2\t5\tB
17.7\t7\tB
4.85\t0.5\tC
7.55\t2.5\tC
10.95\t4.5\tC
13.65\t6.5\tC
"""

REGRESSION_TARGET_DATA = """adcc\tafucose\tgroup
0\t1\tA
0\t3.5\tB
0\t5.5\tC
0\t8\tA
"""

ATTRIBUTE_CONTROL_CHART_DATA = """defectives\tsample_size
6\t20
"""

GRAPH_LAYOUT_DATA = """temperature_c\tpressure_bar\tcycle_time_s\tcatalyst_pct
60\t5\t30\t0.5
62\t6\t34\t0.7
64\t7\t39\t0.9
66\t8\t43\t1.1
68\t9\t47\t1.3
70\t10\t52\t1.5
72\t11\t56\t1.7
74\t12\t61\t1.9
76\t13\t65\t2.1
78\t14\t69\t2.3
80\t15\t74\t2.5
82\t16\t78\t2.7
"""

GROUPED_HYPOTHESIS_DATA = """production_line\tyield_pct\ttimestamp\ttest_measure\treference_measure
A\t91.0\t2026-01-01T00:00:00\t10.1\t10.0
A\t92.0\t2026-01-01T01:00:00\t10.2\t10.1
A\t90.5\t2026-01-01T02:00:00\t9.9\t10.0
A\t91.5\t2026-01-01T03:00:00\t10.1\t10.0
B\t94.0\t2026-01-01T00:00:00\t10.2\t10.1
B\t95.0\t2026-01-01T01:00:00\t10.3\t10.2
B\t93.5\t2026-01-01T02:00:00\t10.0\t10.1
B\t94.5\t2026-01-01T03:00:00\t10.2\t10.1
C\t97.0\t2026-01-01T00:00:00\t10.1\t10.0
C\t98.0\t2026-01-01T01:00:00\t10.2\t10.1
C\t96.5\t2026-01-01T02:00:00\t10.0\t10.1
C\t97.5\t2026-01-01T03:00:00\t10.3\t10.2
"""

EQUIVALENCE_DESIGN_DATA = """production_line\tyield_pct\ttest_measure\treference_measure
A\t100.0\t10.1\t10.0
A\t100.2\t10.2\t10.1
A\t99.9\t9.9\t10.0
A\t100.1\t10.1\t10.0
B\t100.1\t10.2\t10.1
B\t100.0\t10.3\t10.2
B\t100.2\t10.0\t10.1
B\t99.9\t10.2\t10.1
"""

PASTE_GRID_REVIEW_DATA = """이름\t값\t메모\r
검토 A\t1\t긴 값 전체 확인\r
검토 B\t2\t\r
검토 C\t3"""

ATTRIBUTE_CONTROL_BASELINE_DATA = """defectives\tsample_size
8\t20
12\t20
8\t20
12\t20
8\t20
12\t20
8\t20
12\t20
8\t20
12\t20
8\t20
12\t20
8\t20
12\t20
8\t20
12\t20
8\t20
12\t20
8\t20
12\t20
"""

REPORTING_SUMMARY_DATA = """production_line\tyield_pct\ttemperature_c\tpressure_bar
A\t90.0\t60\t5.0
A\t91.0\t61\t5.5
A\t89.0\t62\t6.0
A\t92.0\t63\t6.5
A\t88.0\t64\t7.0
A\t90.5\t65\t7.5
A\t91.5\t66\t8.0
A\t89.5\t67\t8.5
A\t92.5\t68\t9.0
A\t87.5\t69\t9.5
B\t94.0\t70\t10.0
B\t94.5\t71\t10.5
B\t93.5\t72\t11.0
B\t94.2\t73\t11.5
B\t93.8\t74\t12.0
B\t94.1\t75\t12.5
B\t94.3\t76\t13.0
B\t93.7\t77\t13.5
B\t94.4\t78\t14.0
B\t93.6\t79\t14.5
C\t95.0\t80\t15.0
C\t98.0\t81\t15.5
C\t92.0\t82\t16.0
C\t100.0\t83\t16.5
C\t90.0\t84\t17.0
C\t97.0\t85\t17.5
C\t93.0\t86\t18.0
C\t99.0\t87\t18.5
C\t91.0\t88\t19.0
C\t96.0\t89\t19.5
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the DataLab Studio critical-path browser E2E smoke test.",
    )
    parser.add_argument("--backend-port", type=int, default=8011)
    parser.add_argument("--frontend-port", type=int, default=5199)
    parser.add_argument("--workspace-root", type=Path, default=None)
    parser.add_argument("--diagnostics-root", type=Path, default=None)
    parser.add_argument("--keep-workspace", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    if args.workspace_root is None:
        workspace_root = Path(tempfile.mkdtemp(prefix="datalab-e2e-"))
    else:
        args.workspace_root.mkdir(parents=True, exist_ok=True)
        workspace_root = Path(tempfile.mkdtemp(prefix="run-", dir=args.workspace_root))
    diagnostics_root = (
        args.diagnostics_root if args.diagnostics_root is not None else workspace_root
    )
    diagnostics = E2EDiagnostics(diagnostics_root)
    diagnostics.record("E2E diagnostics initialized")
    log_root = diagnostics.log_root
    managed_processes: list[ManagedProcess] = []
    log_handles = []

    backend_base_url = f"http://127.0.0.1:{args.backend_port}"
    frontend_base_url = f"http://127.0.0.1:{args.frontend_port}"

    try:
        backend_env = os.environ.copy()
        backend_env.update(
            {
                "DATALAB_WORKSPACE_ROOT": str(workspace_root / "workspace"),
                "DATALAB_BIND_HOST": "127.0.0.1",
                "DATALAB_BIND_PORT": str(args.backend_port),
                "DATALAB_CORS_ALLOWED_ORIGINS": json.dumps([frontend_base_url]),
            },
        )
        frontend_env = os.environ.copy()
        frontend_env.update(
            {
                "VITE_API_BASE_URL": backend_base_url,
            },
        )

        backend_log_path = log_root / "backend.log"
        frontend_log_path = log_root / "frontend.log"
        backend_log = backend_log_path.open("wb")
        frontend_log = frontend_log_path.open("wb")
        log_handles.extend([backend_log, frontend_log])

        backend_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--app-dir",
                "backend",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.backend_port),
            ],
            cwd=repo_root,
            env=backend_env,
            stdout=backend_log,
            stderr=subprocess.STDOUT,
        )
        managed_processes.append(
            ManagedProcess("backend", backend_process, backend_log_path)
        )
        frontend_process = subprocess.Popen(
            [
                npm_command(),
                "--prefix",
                "frontend",
                "run",
                "dev",
                "--",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.frontend_port),
                "--strictPort",
            ],
            cwd=repo_root,
            env=frontend_env,
            stdout=frontend_log,
            stderr=subprocess.STDOUT,
        )
        managed_processes.append(
            ManagedProcess("frontend", frontend_process, frontend_log_path)
        )

        diagnostics.step("wait for backend health")
        wait_for_url(
            f"{backend_base_url}/api/v1/health",
            "backend health",
            managed_processes,
            diagnostics,
        )
        diagnostics.step("wait for frontend dev server")
        wait_for_url(
            frontend_base_url, "frontend dev server", managed_processes, diagnostics
        )
        run_browser_flow(frontend_base_url, diagnostics)
        print("E2E critical path passed")
        return 0
    except Exception as exc:
        print(f"E2E critical path failed: {exc}", file=sys.stderr)
        print_recent_logs(log_root)
        return 1
    finally:
        for managed_process in managed_processes:
            terminate_process(managed_process.process)
        for handle in log_handles:
            handle.close()
        if args.keep_workspace:
            print(f"Kept E2E workspace: {workspace_root}")
            print(f"Kept E2E diagnostics: {diagnostics.root}")
        else:
            shutil.rmtree(workspace_root, ignore_errors=True)


@dataclass(frozen=True)
class ManagedProcess:
    label: str
    process: subprocess.Popen[bytes]
    log_path: Path


def npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def wait_for_url(
    url: str,
    label: str,
    managed_processes: Sequence[ManagedProcess],
    diagnostics: "E2EDiagnostics",
    timeout_seconds: float = 60.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        for managed_process in managed_processes:
            return_code = managed_process.process.poll()
            if return_code is not None:
                message = (
                    f"[e2e] {managed_process.label} process exited early while waiting for "
                    f"{label} with exit code {return_code}"
                )
                print(message, file=sys.stderr)
                diagnostics.record(message)
                print_log_tail(managed_process.log_path, managed_process.label)
                raise RuntimeError(
                    f"{label} dependency {managed_process.label} exited early with "
                    f"{return_code}; see logs/{managed_process.log_path.name}"
                )
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
        time.sleep(0.5)
    message = (
        f"[e2e] {label} readiness timed out at {url}; printing recent process logs"
    )
    print(message, file=sys.stderr)
    diagnostics.record(message)
    for managed_process in managed_processes:
        print_log_tail(managed_process.log_path, managed_process.label)
    raise TimeoutError(f"{label} did not become ready at {url}: {last_error}")


@dataclass(frozen=True)
class E2EDiagnostics:
    root: Path
    current_step_label: str = field(default="startup", init=False, compare=False)

    def __post_init__(self) -> None:
        self.log_root.mkdir(parents=True, exist_ok=True)
        self.screenshot_root.mkdir(parents=True, exist_ok=True)
        self.html_root.mkdir(parents=True, exist_ok=True)

    @property
    def log_root(self) -> Path:
        return self.root / "logs"

    @property
    def screenshot_root(self) -> Path:
        return self.root / "screenshots"

    @property
    def html_root(self) -> Path:
        return self.root / "html"

    @property
    def summary_log_path(self) -> Path:
        return self.log_root / "e2e-diagnostics.log"

    def record(self, message: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.summary_log_path.open("a", encoding="utf-8") as summary_log:
            summary_log.write(f"{timestamp} {message}\n")

    def step(self, label: str) -> None:
        object.__setattr__(self, "current_step_label", label)
        message = f"[e2e] {label}"
        print(message)
        self.record(message)

    def current_step_slug(self) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "-", self.current_step_label.lower()).strip("-")
        return slug[:64] if slug else "unknown-step"

    def artifact_label(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.name

    def capture_page_failure(self, page: Page | None) -> None:
        if page is None:
            message = "[e2e] no browser page was created before failure"
            print(message, file=sys.stderr)
            self.record(message)
            return

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        step_slug = self.current_step_slug()
        screenshot_path = self.screenshot_root / f"failure-{step_slug}-{timestamp}.png"
        html_path = self.html_root / f"failure-{step_slug}-{timestamp}.html"
        try:
            messages = [
                f"[e2e] failure current URL: {page.url}",
                f"[e2e] failure page title: {page.title()}",
            ]
            for message in messages:
                print(message, file=sys.stderr)
                self.record(message)
        except Exception as exc:
            message = f"[e2e] could not read page location/title: {exc}"
            print(message, file=sys.stderr)
            self.record(message)
        try:
            page.screenshot(path=str(screenshot_path), full_page=True)
            message = (
                f"[e2e] failure screenshot: {self.artifact_label(screenshot_path)}"
            )
            print(message, file=sys.stderr)
            self.record(message)
        except Exception as exc:
            message = f"[e2e] could not write failure screenshot: {exc}"
            print(message, file=sys.stderr)
            self.record(message)
        try:
            html_path.write_text(page.content(), encoding="utf-8")
            message = f"[e2e] failure HTML snapshot: {self.artifact_label(html_path)}"
            print(message, file=sys.stderr)
            self.record(message)
        except Exception as exc:
            message = f"[e2e] could not write failure HTML snapshot: {exc}"
            print(message, file=sys.stderr)
            self.record(message)

    def capture_page(self, page: Page, name: str, *, full_page: bool = True) -> Path:
        screenshot_path = self.screenshot_root / name
        page.screenshot(path=str(screenshot_path), full_page=full_page)
        self.record(f"[e2e] screenshot: {self.artifact_label(screenshot_path)}")
        return screenshot_path

    def capture_locator(self, locator: Locator, name: str) -> Path:
        screenshot_path = self.screenshot_root / name
        locator.screenshot(path=str(screenshot_path))
        self.record(f"[e2e] screenshot: {self.artifact_label(screenshot_path)}")
        return screenshot_path


def verify_localization_shell(
    browser: Browser,
    frontend_base_url: str,
    diagnostics: E2EDiagnostics,
) -> None:
    diagnostics.step("verify English default and persistent Korean switch")
    context = browser.new_context()
    page = context.new_page()
    try:
        page.goto(frontend_base_url, wait_until="networkidle")
        expect(page.locator("html")).to_have_attribute("lang", "en")
        expect(page.get_by_role("button", name="English")).to_have_attribute(
            "aria-pressed", "true"
        )
        expect(page.get_by_text("API ready", exact=True)).to_be_visible(timeout=15_000)
        for label in (
            "Home",
            "Datasets",
            "Analysis",
            "Graphs",
            "Reports",
            "Manage",
            "Help",
        ):
            expect(page.get_by_text(label, exact=True).first).to_be_visible()
        for module_label in (
            "Exploratory Analysis",
            "Hypothesis Tests",
            "Categorical Data Analysis",
            "Correlation and Regression",
            "Quality Control",
            "Design of Experiments",
        ):
            expect(page.get_by_text(module_label, exact=True).first).to_be_visible()

        visible_hangul = page.evaluate(
            """() => {
              const text = document.body.innerText;
              const attributes = Array.from(document.querySelectorAll('[aria-label], [title], [placeholder], [alt]'))
                .flatMap((node) => ['aria-label', 'title', 'placeholder', 'alt'].map((name) => node.getAttribute(name) || ''))
                .join('\\n');
              return (text + '\\n' + attributes).match(/[가-힣]+/g) || [];
            }"""
        )
        assert (
            visible_hangul == []
        ), f"English UI contains Hangul: {visible_hangul[:20]}"
        diagnostics.capture_page(page, "home-en.png")
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(250)
        expect(page.get_by_role("button", name="English")).to_be_visible()
        expect(page.get_by_text("API ready", exact=True)).to_be_visible()
        assert_mobile_locale_controls(page, "English", "API ready")
        assert page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
        )
        diagnostics.capture_page(page, "mobile-en.png")
        page.set_viewport_size({"width": 1280, "height": 800})

        page.goto(f"{frontend_base_url}/help?section=purpose", wait_until="networkidle")
        page.locator(".help-search-field input").fill("regression")
        diagnostics.capture_page(page, "help-en.png")
        route_before = page.url
        page.evaluate("window.__localeStateMarker = 'preserved'")
        page.get_by_role("button", name="Korean").click()
        expect(page.locator("html")).to_have_attribute("lang", "ko")
        expect(page.get_by_text("도움말", exact=True).first).to_be_visible()
        expect(page.locator(".help-search-field input")).to_have_value("regression")
        assert page.url == route_before
        assert page.evaluate("window.__localeStateMarker") == "preserved"
        expect(page.get_by_role("button", name="한국어")).to_have_attribute(
            "aria-pressed", "true"
        )
        assert (
            page.evaluate("window.localStorage.getItem('statistical-twin.locale')")
            == "ko"
        )
        diagnostics.capture_page(page, "help-ko.png")

        page.reload(wait_until="networkidle")
        expect(page.locator("html")).to_have_attribute("lang", "ko")
        expect(page.get_by_role("button", name="한국어")).to_have_attribute(
            "aria-pressed", "true"
        )
        page.get_by_text("홈", exact=True).first.click()
        diagnostics.capture_page(page, "home-ko.png")
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(250)
        expect(page.get_by_role("button", name="한국어")).to_be_visible()
        expect(page.get_by_text("API 준비됨", exact=True)).to_be_visible()
        assert_mobile_locale_controls(page, "한국어", "API 준비됨")
        assert page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
        )
        diagnostics.capture_page(page, "mobile-ko.png")
    finally:
        context.close()


def assert_mobile_locale_controls(page: Page, language: str, api_status: str) -> None:
    sidebar_box = page.locator(".sidebar").bounding_box()
    language_box = page.get_by_role("button", name=language).bounding_box()
    api_box = page.get_by_text(api_status, exact=True).bounding_box()
    assert sidebar_box is not None and sidebar_box["x"] + sidebar_box["width"] <= 1
    assert language_box is not None and api_box is not None
    assert language_box["x"] + language_box["width"] <= api_box["x"]
    assert language_box["y"] < api_box["y"] + api_box["height"]
    assert api_box["y"] < language_box["y"] + language_box["height"]


def run_browser_flow(frontend_base_url: str, diagnostics: E2EDiagnostics) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page: Page | None = None
        try:
            verify_localization_shell(browser, frontend_base_url, diagnostics)
            context = browser.new_context(accept_downloads=True)
            context.add_init_script(
                "window.localStorage.setItem('statistical-twin.locale', 'ko');"
            )
            page = context.new_page()
            diagnostics.step("open Workbench")
            page.goto(frontend_base_url, wait_until="networkidle")
            verify_browser_branding(page, frontend_base_url, diagnostics)

            expect(page.get_by_role("img", name="Samsung Bioepis")).to_be_visible()
            expect(
                page.get_by_role("heading", name="Statistical Twin", exact=True)
            ).to_be_visible()
            expect(page.get_by_text("API 준비됨")).to_be_visible(timeout=15_000)
            expect(page).to_have_url(re.compile(r"/(?:home)?(?:\?|$)"))
            expect(
                page.get_by_role(
                    "heading", name="Statistical Twin 대시보드", exact=True
                )
            ).to_be_visible()
            open_primary_navigation(page, "데이터셋")
            diagnostics.step("paste synthetic TSV and confirm schema")

            paste_plain_text(page, PASTE_GRID_REVIEW_DATA)
            expect(page.get_by_text("4행 x 3열", exact=True).first).to_be_visible()
            expect(page.get_by_text("must-not-render", exact=True)).to_have_count(0)
            expect(page.locator(".paste-summary")).to_contain_text("빈 셀1")
            expect(page.locator(".paste-summary")).to_contain_text("열 수가 다른 행1")
            expect(
                page.get_by_text("행마다 열 수가 다릅니다.", exact=False)
            ).to_be_visible()
            long_preview_cell = page.locator(".paste-preview-grid td").filter(
                has_text="긴 값 전체 확인"
            )
            long_preview_cell.focus()
            expect(
                page.locator(".cell-inspector-value").filter(has_text="긴 값 전체 확인")
            ).to_be_visible()
            long_preview_cell.press("ArrowLeft")
            expect(
                page.locator(".cell-inspector-value").filter(has_text="1")
            ).to_be_visible()

            failed_paste_contents: list[str] = []

            def fail_paste_request(route) -> None:
                request_payload = route.request.post_data_json
                failed_paste_contents.append(request_payload["content"])
                route.fulfill(
                    status=503,
                    content_type="application/json",
                    body=json.dumps({"error": {"code": "dataset_paste_test_failure"}}),
                )

            page.route("**/api/v1/datasets/paste", fail_paste_request)
            page.get_by_role("button", name="붙여넣기 데이터 등록").click()
            expect(page.get_by_text("dataset_paste_test_failure")).to_be_visible()
            assert failed_paste_contents == [PASTE_GRID_REVIEW_DATA]
            page.get_by_role("button", name="원문 보기").click()
            expect(page.get_by_label("붙여넣기 원문")).to_have_value(
                PASTE_GRID_REVIEW_DATA.replace("\r\n", "\n")
            )
            page.unroute("**/api/v1/datasets/paste")
            page.reload(wait_until="networkidle")
            expect(page.get_by_label("붙여넣기 원문")).to_have_value("")

            paste_plain_text(page, SAMPLE_DATA)
            expect(page.get_by_text("7행 x 2열", exact=True).first).to_be_visible()
            page.get_by_role("button", name="붙여넣기 데이터 등록").click()
            expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(
                timeout=15_000
            )
            expect(page.get_by_label("붙여넣기 원문")).to_have_value("")

            page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
            expect(page.locator("#version-title")).to_contain_text("v1", timeout=20_000)
            expect_dataset_context_counts(page, row_label="6행", column_label="2컬럼")
            page.get_by_label("미리보기 페이지 크기").select_option("25")
            expect(page.get_by_label("미리보기 페이지 크기")).to_have_value("25")
            page.locator(".canonical-preview-grid tbody tr").first.locator("td").nth(
                1
            ).click()
            expect(
                page.locator(".canonical-preview-section .cell-inspector-value").filter(
                    has_text="10"
                )
            ).to_be_visible()
            diagnostics.step("create an immutable version from one cell correction")
            verify_dataset_cell_correction(page)
            page.reload(wait_until="networkidle")
            expect(page.locator("#version-title")).to_contain_text("v2", timeout=20_000)
            expect(page.get_by_label("붙여넣기 원문")).to_have_value("")
            expect_dataset_context_counts(page, row_label="6행", column_label="2컬럼")

            diagnostics.step("verify project dashboard alignment and brand links")
            verify_project_dashboard(page, diagnostics)
            verify_sidebar_group_toggle(page, diagnostics)
            open_primary_navigation(page, "분석")
            verify_active_dataset_analysis_alignment(page, diagnostics)
            expect(page.locator("#workbench-title")).to_have_text("기술통계")
            page.get_by_role("button", name="기술통계 실행").click()
            diagnostics.step("run descriptive statistics")
            descriptive_row = page.locator(".analysis-run-panel .result-table tbody tr")
            descriptive_row.wait_for(state="attached", timeout=20_000)
            if "Value" not in descriptive_row.inner_text():
                raise AssertionError("descriptive result row did not contain Value")

            diagnostics.step("verify graph builder box plot preview")
            verify_graph_builder_box_plot(page)

            open_primary_navigation(page, "분석")
            select_method_card(page, "가설 검정", "2-표본 t-검정")
            expect(page.locator("#workbench-title")).to_have_text("2-표본 t-검정")
            page.get_by_role("button", name="2-표본 t-검정 실행").click()
            diagnostics.step("run two-sample t test")
            expect(
                page.locator(".result-table").filter(has_text="Hedges g")
            ).to_be_visible(
                timeout=20_000,
            )
            capture_hypothesis_method_cards(page, diagnostics)

            diagnostics.step("create, download, and delete one export")
            create_exports(page)
            diagnostics.step("verify Help Report Project and Manage routes")
            verify_help_report_and_manage_routes(page, diagnostics)
            diagnostics.step("restore and compare saved results")
            restore_and_compare_saved_results(page)
            diagnostics.step("delete one stored analysis run")
            delete_one_saved_analysis_run(page)
            diagnostics.step("verify schema stale behavior")
            verify_schema_stale_behavior(page)
            diagnostics.step("verify linear model fit and prediction")
            verify_linear_model_fit_and_prediction(page, diagnostics)
            diagnostics.step("verify attribute control chart")
            verify_attribute_control_chart(page)
            diagnostics.step("verify reporting summary variance and fixed-Y scatter")
            verify_reporting_summary_variance_and_scatter(page, diagnostics)
            diagnostics.step("verify DOE factorial analysis")
            verify_doe_factorial_analysis(page, diagnostics)
            diagnostics.step("verify DOE response surface analysis and optimization")
            verify_doe_response_surface_analysis(page, diagnostics)
            diagnostics.step("verify standalone LHS design and response revision")
            verify_latin_hypercube_design(page, diagnostics)
            diagnostics.step("verify Bayesian study observations and recommendation")
            verify_bayesian_optimization(page, diagnostics)
            diagnostics.step("verify XLSX browser upload")
            verify_xlsx_file_upload(
                page, Path(tempfile.mkdtemp(prefix="datalab-e2e-upload-"))
            )
            diagnostics.step("verify CSV upload and upload error recovery")
            verify_csv_file_upload_and_error_recovery(
                page,
                Path(tempfile.mkdtemp(prefix="datalab-e2e-csv-upload-")),
            )
            diagnostics.step("verify parser option editing")
            verify_parser_option_editing(
                page,
                Path(tempfile.mkdtemp(prefix="datalab-e2e-parser-options-")),
            )
            diagnostics.step("verify delimiter option editing")
            verify_delimiter_option_editing(
                page,
                Path(tempfile.mkdtemp(prefix="datalab-e2e-delimiter-options-")),
            )
            diagnostics.step("verify XLSX sheet selection recovery")
            verify_xlsx_sheet_selection(
                page,
                Path(tempfile.mkdtemp(prefix="datalab-e2e-xlsx-sheet-")),
            )
            diagnostics.step("verify CP949 encoding selection recovery")
            verify_text_encoding_selection(
                page,
                Path(tempfile.mkdtemp(prefix="datalab-e2e-encoding-options-")),
            )
            diagnostics.step("verify descriptive quick charts and run chart p-values")
            verify_descriptive_quick_charts_and_run_chart(page)
            diagnostics.step("verify graph layout refinements")
            verify_graph_layout_refinements(page, diagnostics)
            diagnostics.step("verify grouped graphs and hypothesis extensions")
            verify_grouped_graphs_and_hypothesis_extensions(page, diagnostics)
            diagnostics.step("verify lazy panel direct routes")
            verify_lazy_panel_direct_routes(page, frontend_base_url)
            diagnostics.step("verify lazy panel error boundary")
            verify_lazy_panel_error_boundary(context, frontend_base_url)
        except PlaywrightTimeoutError as exc:
            message = (
                f"Playwright wait timed out during '{diagnostics.current_step_label}': "
                f"{describe_page(page)}"
            )
            diagnostics.record(f"[e2e] {message}")
            diagnostics.capture_page_failure(page)
            raise AssertionError(message) from exc
        except Exception:
            diagnostics.capture_page_failure(page)
            raise
        finally:
            browser.close()


def describe_page(page: Page | None) -> str:
    if page is None:
        return "browser page was not created"
    title = "<unavailable>"
    try:
        title = page.title()
    except Exception as exc:
        title = f"<unavailable: {exc}>"
    return f"current URL: {page.url}; page title: {title}"


def verify_browser_branding(
    page: Page,
    frontend_base_url: str,
    diagnostics: E2EDiagnostics,
) -> None:
    expect(page).to_have_title("Statistical Twin")
    favicon = page.locator('link[rel~="icon"]')
    expect(favicon).to_have_count(1)
    favicon_href = favicon.get_attribute("href")
    if favicon_href != "/statistical-twin-favicon-v1.svg":
        raise AssertionError(f"unexpected favicon href: {favicon_href}")
    favicon_response = page.request.get(
        f"{frontend_base_url}/statistical-twin-favicon-v1.svg"
    )
    if favicon_response.status != 200:
        raise AssertionError(f"favicon request returned HTTP {favicon_response.status}")
    favicon_text = favicon_response.text()
    if "<svg" not in favicon_text or "<script" in favicon_text.lower():
        raise AssertionError("favicon response was not the expected safe SVG")
    metadata_path = diagnostics.root / "statistical-twin-head-metadata.txt"
    metadata_path.write_text(
        "\n".join(
            [
                f"document.title={page.title()}",
                f"favicon.href={favicon_href}",
                f"favicon.status={favicon_response.status}",
                f"favicon.content-type={favicon_response.headers.get('content-type', '')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    diagnostics.record(
        f"[e2e] browser head metadata: {diagnostics.artifact_label(metadata_path)}"
    )


def _computed_style(locator: Locator, properties: list[str]) -> dict[str, str]:
    return locator.evaluate(
        """
        (element, propertyNames) => {
          const style = getComputedStyle(element);
          return Object.fromEntries(
            propertyNames.map((propertyName) => [propertyName, style[propertyName]])
          );
        }
        """,
        properties,
    )


def _pixel_value(value: str) -> float:
    return float(value[:-2] if value.endswith("px") else value)


def assert_doe_table_visual_consistency(
    root: Locator,
    diagnostics: E2EDiagnostics,
    label: str,
) -> None:
    expect(root.locator(".doe-settings-matrix")).to_have_count(0)
    settings_table = root.locator("table.doe-settings-table").first
    factor_table = root.locator("table.doe-factor-table").first
    expect(settings_table).to_be_visible()
    expect(factor_table).to_be_visible()

    header_properties = [
        "backgroundColor",
        "color",
        "fontSize",
        "fontWeight",
        "paddingTop",
        "paddingBottom",
    ]
    settings_header = _computed_style(
        settings_table.locator("thead th").first, header_properties
    )
    factor_header = _computed_style(
        factor_table.locator("thead th").first, header_properties
    )
    for property_name in ("backgroundColor", "color", "fontSize", "fontWeight"):
        if settings_header[property_name] != factor_header[property_name]:
            raise AssertionError(
                f"{label} header {property_name} mismatch: "
                f"{settings_header[property_name]} != {factor_header[property_name]}"
            )
    for property_name in ("paddingTop", "paddingBottom"):
        difference = abs(
            _pixel_value(settings_header[property_name])
            - _pixel_value(factor_header[property_name])
        )
        if difference > 1:
            raise AssertionError(
                f"{label} header {property_name} differed by {difference}px"
            )

    settings_control = settings_table.locator(
        "tbody tr.compact-settings-control-row input:not([type=checkbox]), "
        "tbody tr.compact-settings-control-row select"
    ).first
    factor_control = factor_table.locator("tbody input, tbody select").first
    input_properties = [
        "fontSize",
        "borderRadius",
        "borderColor",
        "paddingTop",
        "paddingBottom",
        "paddingLeft",
        "paddingRight",
    ]
    settings_input = _computed_style(settings_control, input_properties)
    factor_input = _computed_style(factor_control, input_properties)
    settings_box = settings_control.bounding_box()
    factor_box = factor_control.bounding_box()
    if settings_box is None or factor_box is None:
        raise AssertionError(f"{label} input bounding box unavailable")
    if abs(settings_box["height"] - factor_box["height"]) > 2:
        raise AssertionError(
            f"{label} input heights differ: "
            f"{settings_box['height']} != {factor_box['height']}"
        )
    for property_name in ("fontSize", "borderRadius", "borderColor"):
        if settings_input[property_name] != factor_input[property_name]:
            raise AssertionError(
                f"{label} input {property_name} mismatch: "
                f"{settings_input[property_name]} != {factor_input[property_name]}"
            )
    for property_name in ("paddingTop", "paddingBottom", "paddingLeft", "paddingRight"):
        difference = abs(
            _pixel_value(settings_input[property_name])
            - _pixel_value(factor_input[property_name])
        )
        if difference > 1:
            raise AssertionError(
                f"{label} input {property_name} differed by {difference}px"
            )

    section_properties = settings_table.evaluate(
        """
        (table) => {
          const section = table.closest('section');
          const heading = section?.querySelector('h4, h5');
          if (!section || !heading) return null;
          const sectionStyle = getComputedStyle(section);
          const headingStyle = getComputedStyle(heading);
          return {
            borderRadius: sectionStyle.borderRadius,
            paddingTop: sectionStyle.paddingTop,
            paddingRight: sectionStyle.paddingRight,
            paddingBottom: sectionStyle.paddingBottom,
            paddingLeft: sectionStyle.paddingLeft,
            headingFontSize: headingStyle.fontSize,
          };
        }
        """
    )
    factor_section_properties = factor_table.evaluate(
        """
        (table) => {
          const section = table.closest('section');
          const heading = section?.querySelector('h4, h5');
          if (!section || !heading) return null;
          const sectionStyle = getComputedStyle(section);
          const headingStyle = getComputedStyle(heading);
          return {
            borderRadius: sectionStyle.borderRadius,
            paddingTop: sectionStyle.paddingTop,
            paddingRight: sectionStyle.paddingRight,
            paddingBottom: sectionStyle.paddingBottom,
            paddingLeft: sectionStyle.paddingLeft,
            headingFontSize: headingStyle.fontSize,
          };
        }
        """
    )
    if section_properties is None or factor_section_properties is None:
        raise AssertionError(f"{label} section styles unavailable")
    for property_name in ("borderRadius", "headingFontSize"):
        if (
            section_properties[property_name]
            != factor_section_properties[property_name]
        ):
            raise AssertionError(
                f"{label} section {property_name} mismatch: "
                f"{section_properties[property_name]} != "
                f"{factor_section_properties[property_name]}"
            )
    for property_name in ("paddingTop", "paddingRight", "paddingBottom", "paddingLeft"):
        difference = abs(
            _pixel_value(section_properties[property_name])
            - _pixel_value(factor_section_properties[property_name])
        )
        if difference > 2:
            raise AssertionError(
                f"{label} section {property_name} differed by {difference}px"
            )
    diagnostics.record(
        f"[e2e] {label} DOE table style match "
        f"header={settings_header} input-height={settings_box['height']:.2f}px "
        f"factor-input-height={factor_box['height']:.2f}px"
    )


def select_option_by_label_without_retry(select: Locator, label: str) -> None:
    select.wait_for(state="visible", timeout=15_000)
    select.evaluate(
        """
        (element, optionLabel) => {
          const option = Array.from(element.options).find(
            (candidate) => candidate.textContent?.trim() === optionLabel,
          );
          if (!option) throw new Error(`option not found: ${optionLabel}`);
          element.value = option.value;
          element.dispatchEvent(new Event("change", { bubbles: true }));
        }
        """,
        label,
    )


def select_method_card(page: Page, module_label: str, method_label: str) -> None:
    module_button = page.get_by_role("navigation", name="분석 모듈").get_by_role(
        "button", name=re.compile(rf"^{re.escape(module_label)}")
    )
    module_button.wait_for(state="visible", timeout=15_000)
    module_button.evaluate("(button) => button.click()")
    if module_label == "가설 검정":
        family_method = page.locator(".hypothesis-family-methods").get_by_role(
            "button", name=method_label, exact=True
        )
        family_method.wait_for(state="visible", timeout=15_000)
        family_method.evaluate("(button) => button.click()")
        return
    method_card = page.locator(".method-item").filter(has_text=method_label)
    method_card.wait_for(state="visible", timeout=15_000)
    method_card.evaluate("(button) => button.click()")


def capture_hypothesis_method_cards(page: Page, diagnostics: E2EDiagnostics) -> None:
    family_grid = page.locator(".hypothesis-family-grid")
    families = family_grid.locator(".hypothesis-family-card")
    expect(families).to_have_count(4)
    expect(family_grid.get_by_role("button")).to_have_count(10)
    for family_label in ("t-검정", "동등성 검정", "분산분석", "비모수 검정"):
        expect(family_grid).to_contain_text(family_label)
    assert_children_do_not_overlap(family_grid, families, "hypothesis families")
    diagnostics.capture_locator(
        family_grid,
        "hypothesis-family-cards.png",
    )


def open_primary_navigation(page: Page, label: str) -> None:
    group = page.locator(".sidebar-group").filter(
        has=page.locator(".sidebar-group-control").filter(
            has_text=re.compile(rf"^{re.escape(label)}$")
        )
    )
    control = group.locator(".sidebar-group-control")
    if control.get_attribute("aria-controls") is None:
        control.click()
        return
    if control.get_attribute("aria-expanded") != "true":
        control.click()
    active_method = group.locator('.sidebar-method-button[aria-current="page"]')
    if active_method.count() > 0:
        active_method.first.click()
        return
    active_leaf = group.locator('.sidebar-submenu-button[aria-current="page"]')
    if active_leaf.count() > 0:
        active_leaf.first.click()
        return
    direct_leaf = group.locator(
        ".sidebar-submenu-button:not([aria-controls]):not(:disabled)"
    )
    if direct_leaf.count() > 0:
        direct_leaf.first.click()
        return
    module = group.locator(
        ".sidebar-submenu-button[aria-controls]:not(:disabled)"
    ).first
    if module.get_attribute("aria-expanded") != "true":
        module.click()
    group.locator(".sidebar-method-button:not(:disabled)").first.click()


def verify_sidebar_group_toggle(page: Page, diagnostics: E2EDiagnostics) -> None:
    group = page.locator(".sidebar-group").filter(
        has=page.locator(".sidebar-group-control").filter(has_text=re.compile("^분석$"))
    )
    control = group.locator(".sidebar-group-control")
    expect(control).to_have_attribute("aria-expanded", "true")
    modules = group.locator(".sidebar-tree-level-0")
    expect(modules).to_have_count(6)
    exploration = group.locator(".sidebar-tree-level-0").filter(
        has=page.locator(".sidebar-submenu-button").filter(
            has_text=re.compile("^탐색적 분석$")
        )
    )
    exploration_control = exploration.locator(".sidebar-submenu-button")
    expect(exploration_control).to_have_attribute("aria-expanded", "false")
    expect(exploration.locator(".sidebar-method-list")).to_be_hidden()
    exploration_control.click()
    expect(exploration_control).to_have_attribute("aria-expanded", "true")
    methods = exploration.locator(".sidebar-method-button")
    expect(methods).to_have_count(4)
    expect(methods).to_contain_text(
        ["기술통계", "그래프 요약", "정규성 검정", "등분산 검정"]
    )
    methods.filter(has_text=re.compile("^정규성 검정$")).click()
    expect(page).to_have_url(re.compile(r"/analysis/exploration/eda\.normality"))
    expect(group.locator('.sidebar-method-button[aria-current="page"]')).to_have_text(
        "정규성 검정"
    )
    diagnostics.capture_page(page, "sidebar-analysis-method-hierarchy.png")
    group.locator(".sidebar-submenu-button").filter(
        has_text=re.compile("^탐색적 분석$")
    ).click()
    group.locator(".sidebar-submenu-button").filter(
        has_text=re.compile("^탐색적 분석$")
    ).click()
    group.locator(".sidebar-method-button").filter(
        has_text=re.compile("^기술통계$")
    ).click()
    current_url = page.url
    control.click()
    expect(control).to_have_attribute("aria-expanded", "false")
    expect(group.locator(".sidebar-submenu")).to_be_hidden()
    if page.url != current_url:
        raise AssertionError("sidebar group toggle unexpectedly navigated")
    diagnostics.capture_page(page, "sidebar-collapsed-analysis.png")
    control.click()
    expect(control).to_have_attribute("aria-expanded", "true")


def verify_project_dashboard(page: Page, diagnostics: E2EDiagnostics) -> None:
    page.set_viewport_size({"width": 1440, "height": 900})
    page.locator(".brand-home-link").click()
    expect(page).to_have_url(re.compile(r"/home(?:\?|$)"))
    expect(page.locator("#project-overview-title")).to_have_text(
        "Statistical Twin 대시보드"
    )
    expect(page.locator(".home-quick-card")).to_have_count(6)
    expect(page.locator(".project-dashboard-card")).to_have_count(4)
    expect(page.get_by_role("heading", name="현재 분석 데이터셋")).to_be_visible()
    expect(page.get_by_role("heading", name="데이터셋 현황")).to_be_visible()
    expect(page.get_by_role("heading", name="최근 분석")).to_be_visible()
    expect(page.get_by_role("heading", name="모델 및 리포트")).to_be_visible()
    expect(page.get_by_role("img", name=re.compile(r"수치형 .*개"))).to_be_visible()
    expect(page.locator(".active-dataset-technical")).to_have_count(0)

    assert_active_dataset_outer_alignment(
        page,
        page.locator(".project-dashboard-grid"),
        diagnostics,
        "project dashboard",
    )

    diagnostics.capture_page(page, "project-dashboard-desktop.png")
    diagnostics.capture_page(page, "home-dashboard-wide.png")
    diagnostics.capture_locator(
        page.locator(".main"),
        "project-context-alignment.png",
    )
    diagnostics.capture_page(page, "active-dataset-aligned-project.png")
    diagnostics.capture_locator(
        page.locator(".brand-home-link"),
        "project-brand-home-link.png",
    )

    page.set_viewport_size({"width": 390, "height": 844})
    page.locator(".mobile-brand-home-link").click()
    expect(page).to_have_url(re.compile(r"/home(?:\?|$)"))
    mobile_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth - window.innerWidth"
    )
    if mobile_overflow > 1:
        raise AssertionError(
            f"project dashboard overflowed mobile viewport by {mobile_overflow}px"
        )
    assert_active_dataset_outer_alignment(
        page,
        page.locator(".project-dashboard-grid"),
        diagnostics,
        "mobile project dashboard",
    )
    diagnostics.capture_page(page, "project-dashboard-mobile.png")
    diagnostics.capture_page(page, "home-dashboard-mobile.png")
    diagnostics.capture_page(page, "active-dataset-aligned-mobile.png")
    page.set_viewport_size({"width": 1440, "height": 900})


def assert_active_dataset_outer_alignment(
    page: Page,
    content: Locator,
    diagnostics: E2EDiagnostics,
    label: str,
) -> None:
    dataset_card = page.locator(".active-dataset-card")
    main = page.locator(".main")
    card_box = dataset_card.bounding_box()
    content_box = content.bounding_box()
    main_box = main.bounding_box()
    if card_box is None or content_box is None or main_box is None:
        raise AssertionError(f"{label} outer alignment bounds unavailable")
    left_delta = abs(card_box["x"] - content_box["x"])
    right_delta = abs(
        card_box["x"] + card_box["width"] - content_box["x"] - content_box["width"]
    )
    diagnostics.record(
        f"[e2e] {label} dataset-card edges: left={left_delta:.2f}px "
        f"right={right_delta:.2f}px"
    )
    if left_delta > 2 or right_delta > 2:
        raise AssertionError(
            f"{label} dataset card differed from content by "
            f"left={left_delta:.2f}px right={right_delta:.2f}px"
        )
    if card_box["width"] >= main_box["width"] - 2:
        raise AssertionError(f"{label} dataset card still spans the full main width")
    if card_box["x"] <= main_box["x"] + 2:
        raise AssertionError(f"{label} dataset card has no outer content gutter")


def verify_active_dataset_analysis_alignment(
    page: Page,
    diagnostics: E2EDiagnostics,
) -> None:
    analysis_shell = page.locator(".analysis-shell")
    expect(analysis_shell).to_be_visible()
    assert_active_dataset_outer_alignment(
        page,
        analysis_shell,
        diagnostics,
        "analysis shell",
    )
    diagnostics.capture_page(page, "active-dataset-aligned-analysis.png")


def verify_graph_builder_box_plot(page: Page) -> None:
    open_primary_navigation(page, "그래프")
    expect(page.get_by_role("heading", name="그래프 작성")).to_be_visible(
        timeout=15_000
    )
    value_checkbox = page.get_by_role("checkbox", name="Value")
    if not value_checkbox.is_checked():
        value_checkbox.check()
    page.get_by_role("button", name="그래프 생성", exact=True).click()
    expect(page.get_by_role("heading", name="그래프 결과")).to_be_visible(
        timeout=20_000
    )
    expect(page.get_by_label("그래프 provenance")).to_contain_text("사용 행")
    expect(page.get_by_role("img", name=re.compile(r"Box Plot"))).to_be_visible()
    expect(
        page.get_by_text(
            "이 결과는 미리보기이며 저장 분석 이력, result artifact 또는 export를 만들지 않습니다.",
            exact=True,
        )
    ).to_be_visible()


def verify_graph_layout_refinements(page: Page, diagnostics: E2EDiagnostics) -> None:
    page.set_viewport_size({"width": 1440, "height": 900})


def verify_grouped_graphs_and_hypothesis_extensions(
    page: Page,
    diagnostics: E2EDiagnostics,
) -> None:
    open_primary_navigation(page, "데이터셋")
    paste_plain_text(page, GROUPED_HYPOTHESIS_DATA)
    page.get_by_role("button", name="붙여넣기 데이터 등록").click()
    expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
    page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
    expect(page.locator("#version-title")).to_contain_text("v1", timeout=20_000)
    expect_dataset_context_counts(page, row_label="12행", column_label="5열")

    open_primary_navigation(page, "그래프")
    page.get_by_role("radio", name="수치 변수 1개를 그룹별 비교").check()
    response = page.get_by_role("checkbox", name=re.compile(r"^yield_pct"))
    if not response.is_checked():
        response.check()
    page.locator(".graph-role-option").filter(has_text="그룹 변수").locator(
        "select"
    ).select_option(label="production_line")
    page.get_by_role("button", name="그래프 생성", exact=True).click()
    grouped_box = page.get_by_role("img", name="변수 비교 Box Plot")
    expect(grouped_box).to_be_visible(timeout=20_000)
    expect(grouped_box.locator("[role='img']")).to_have_count(3)
    expect(grouped_box.locator("[tabindex='0']")).to_have_count(1)
    diagnostics.capture_page(page, "grouped-box-plot.png")

    page.locator(".graph-type-button").filter(
        has_text=re.compile("^Individual Value Plot")
    ).click()
    page.get_by_role("button", name="그래프 생성", exact=True).click()
    grouped_individual = page.locator(".graph-preview-grid-individual-value-plot svg")
    expect(grouped_individual).to_have_count(1, timeout=20_000)
    expect(grouped_individual.locator(".individual-value-point")).to_have_count(12)
    diagnostics.capture_page(page, "grouped-individual-value-plot.png")

    page.locator(".graph-type-button").filter(
        has_text=re.compile("^I-MR Chart")
    ).click()
    page.get_by_role("radio", name="수치 변수 1개를 그룹별 비교").check()
    page.locator(".graph-role-option").filter(has_text="그룹 변수").locator(
        "select"
    ).select_option(label="production_line")
    page.get_by_role("button", name="그래프 생성", exact=True).click()
    grouped_imr_cards = page.locator(
        ".graph-preview-grid-imr-chart > .graph-preview-card-full-row"
    )
    expect(grouped_imr_cards).to_have_count(3, timeout=20_000)
    for index in range(3):
        expect(
            grouped_imr_cards.nth(index).locator(".chart-grid > .chart-panel")
        ).to_have_count(2)
    diagnostics.capture_page(page, "grouped-imr.png")

    open_primary_navigation(page, "분석")
    select_method_card(page, "가설 검정", "일원분산분석")
    expect(page.locator("#workbench-title")).to_have_text("일원분산분석")
    page.get_by_label("반응 변수", exact=True).select_option(label="yield_pct")
    page.get_by_label("그룹 변수", exact=True).select_option(label="production_line")
    page.get_by_label("사후비교", exact=True).select_option("tukey_kramer")
    page.get_by_role("button", name="일원분산분석 실행").click()
    expect(page.get_by_label("일원분산분석 요약")).to_contain_text(
        "Tukey-Kramer", timeout=20_000
    )

    page.get_by_label("사후비교", exact=True).select_option("dunnett")
    page.get_by_label("기준 그룹", exact=True).select_option(label="A (N 4)")
    page.get_by_role("button", name="일원분산분석 실행").click()
    expect(page.get_by_label("일원분산분석 요약")).to_contain_text(
        "Dunnett", timeout=20_000
    )
    expect(page.get_by_label("일원분산분석 요약")).to_contain_text("A")
    diagnostics.capture_page(page, "anova-dunnett.png")

    page.get_by_role("radio", name="등분산 가정 안 함").check()
    page.get_by_role("button", name="일원분산분석 실행").click()
    expect(page.get_by_label("일원분산분석 요약")).to_contain_text(
        "Welch", timeout=20_000
    )
    expect(page.get_by_label("일원분산분석 요약")).to_contain_text("Games-Howell")
    diagnostics.capture_page(page, "anova-welch-games-howell.png")

    open_primary_navigation(page, "데이터셋")
    paste_plain_text(page, EQUIVALENCE_DESIGN_DATA)
    page.get_by_role("button", name="붙여넣기 데이터 등록").click()
    expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
    page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
    expect(page.locator("#version-title")).to_contain_text("v1", timeout=20_000)

    open_primary_navigation(page, "분석")
    select_method_card(page, "가설 검정", "2-표본 동등성 검정")
    expect(page.locator("#workbench-title")).to_have_text("2-표본 동등성 검정")
    page.get_by_label("반응 변수", exact=True).select_option(label="yield_pct")
    page.get_by_label("그룹 변수", exact=True).select_option(label="production_line")
    page.get_by_label("시험 그룹", exact=True).select_option(label="B (N 4)")
    page.get_by_label("기준 그룹", exact=True).select_option(label="A (N 4)")
    page.get_by_role("button", name="2-표본 동등성 검정 실행").click()
    expect(page.get_by_label("동등성 검정 요약")).to_contain_text(
        "독립 2-표본 평균 차이", timeout=20_000
    )
    expect(page.get_by_label("동등성 검정 요약")).to_contain_text("B - A")
    diagnostics.capture_page(page, "equivalence-two-sample.png")

    select_method_card(page, "가설 검정", "대응표본 동등성 검정")
    expect(page.locator("#workbench-title")).to_have_text("대응표본 동등성 검정")
    page.get_by_label("시험 측정", exact=True).select_option(label="test_measure")
    page.get_by_label("기준 측정", exact=True).select_option(label="reference_measure")
    page.get_by_role("button", name="대응표본 동등성 검정 실행").click()
    expect(page.get_by_label("동등성 검정 요약")).to_contain_text(
        "대응표본 평균 차이", timeout=20_000
    )
    expect(
        page.get_by_role("img", name=re.compile("시험 측정 - 기준 측정"))
    ).to_be_visible()
    diagnostics.capture_page(page, "equivalence-paired.png")
    open_primary_navigation(page, "데이터셋")
    paste_plain_text(page, GRAPH_LAYOUT_DATA)
    page.get_by_role("button", name="붙여넣기 데이터 등록").click()
    expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
    page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
    expect(page.locator("#version-title")).to_contain_text("v1", timeout=20_000)
    expect_dataset_context_counts(page, row_label="12행", column_label="4열")

    open_primary_navigation(page, "그래프")
    expect(page.get_by_role("heading", name="그래프 작성")).to_be_visible(
        timeout=15_000
    )
    variable_picker = page.locator(".graph-variable-picker").first
    for column_name in (
        "temperature_c",
        "pressure_bar",
        "cycle_time_s",
        "catalyst_pct",
    ):
        checkbox = variable_picker.get_by_role(
            "checkbox", name=re.compile(rf"^{re.escape(column_name)}")
        )
        if not checkbox.is_checked():
            checkbox.check()
    expect(variable_picker).to_contain_text("선택 4 / 12")
    diagnostics.capture_locator(variable_picker, "graph-variable-picker-desktop.png")
    page.get_by_role("radio", name="개별 패널").check()
    page.get_by_role("button", name="그래프 생성", exact=True).click()
    expect(page.get_by_role("heading", name="그래프 결과")).to_be_visible(
        timeout=20_000
    )
    assert_single_chart_cards_fill(page, diagnostics, "graph-preview-grid-box-plot", 4)
    diagnostics.capture_page(page, "graph-box-individual-desktop.png")

    for button_label, grid_class in (
        ("Histogram", "graph-preview-grid-histogram"),
        ("Q-Q Plot", "graph-preview-grid-qq-plot"),
        ("ECDF", "graph-preview-grid-ecdf"),
    ):
        page.locator(".graph-type-button").filter(
            has_text=re.compile(rf"^{re.escape(button_label)}")
        ).click()
        page.get_by_role("button", name="그래프 생성", exact=True).click()
        expect(page.get_by_role("heading", name="그래프 결과")).to_be_visible(
            timeout=20_000
        )
        assert_single_chart_cards_fill(page, diagnostics, grid_class, 4)

    page.locator(".graph-type-button").filter(
        has_text=re.compile("^Individual Value Plot")
    ).click()
    page.get_by_role("button", name="그래프 생성", exact=True).click()
    individual_card = page.locator(
        ".graph-preview-grid-individual-value-plot > .graph-preview-card-full-row"
    )
    expect(individual_card).to_have_count(1, timeout=20_000)
    assert_chart_width_ratio(individual_card, diagnostics, "individual-value")

    page.locator(".graph-type-button").filter(has_text=re.compile("^Run Chart")).click()
    page.get_by_role("button", name="그래프 생성", exact=True).click()
    expect(page.locator(".graph-preview-grid-run-chart .chart-panel")).to_have_count(
        4, timeout=20_000
    )
    diagnostics.capture_page(page, "run-chart-regression.png")

    page.locator(".graph-type-button").filter(
        has_text=re.compile("^I-MR Chart")
    ).click()
    page.get_by_role("button", name="그래프 생성", exact=True).click()
    imr_cards = page.locator(
        ".graph-preview-grid-imr-chart > .graph-preview-card-full-row"
    )
    expect(imr_cards).to_have_count(4, timeout=20_000)
    for index in range(4):
        expect(
            imr_cards.nth(index).locator(".chart-grid > .chart-panel")
        ).to_have_count(2)
    diagnostics.capture_page(page, "imr-paired-layout.png")
    diagnostics.capture_locator(
        page.locator(".active-dataset-selector"),
        "active-dataset-context-desktop.png",
    )

    page.set_viewport_size({"width": 390, "height": 844})
    diagnostics.capture_locator(
        page.locator(".active-dataset-selector"),
        "active-dataset-context-mobile.png",
    )
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth - window.innerWidth"
    )
    if overflow > 1:
        raise AssertionError(f"mobile page overflowed horizontally by {overflow}px")
    page.get_by_role("button", name="주요 메뉴 열기").click()
    analysis_group = page.locator(".sidebar-group").filter(
        has=page.locator(".sidebar-group-control").filter(has_text=re.compile("^분석$"))
    )
    analysis_control = analysis_group.locator(".sidebar-group-control")
    analysis_control.click()
    expect(page.locator("#application-sidebar")).to_have_class(
        re.compile(r"\bis-open\b")
    )
    expect(analysis_control).to_have_attribute("aria-expanded", "false")
    page.keyboard.press("Escape")
    page.set_viewport_size({"width": 1440, "height": 900})


def assert_single_chart_cards_fill(
    page: Page,
    diagnostics: E2EDiagnostics,
    grid_class: str,
    expected_count: int,
) -> None:
    cards = page.locator(f".{grid_class} .graphical-summary-card")
    expect(cards).to_have_count(expected_count)
    for index in range(expected_count):
        assert_chart_width_ratio(
            cards.nth(index), diagnostics, f"{grid_class}-{index + 1}"
        )


def assert_children_do_not_overlap(
    parent: Locator,
    children: Locator,
    label: str,
) -> None:
    parent_box = parent.bounding_box()
    if parent_box is None:
        raise AssertionError(f"{label} parent did not have a bounding box")
    boxes = []
    for index in range(children.count()):
        box = children.nth(index).bounding_box()
        if box is None:
            raise AssertionError(f"{label} child {index + 1} had no bounding box")
        if box["x"] < parent_box["x"] - 1 or (
            box["x"] + box["width"] > parent_box["x"] + parent_box["width"] + 1
        ):
            raise AssertionError(f"{label} child {index + 1} escaped its parent")
        boxes.append(box)
    for left_index, left in enumerate(boxes):
        for right_index, right in enumerate(boxes[left_index + 1 :], left_index + 1):
            horizontal_overlap = min(
                left["x"] + left["width"], right["x"] + right["width"]
            ) - max(left["x"], right["x"])
            vertical_overlap = min(
                left["y"] + left["height"], right["y"] + right["height"]
            ) - max(left["y"], right["y"])
            if horizontal_overlap > 1 and vertical_overlap > 1:
                raise AssertionError(
                    f"{label} children {left_index + 1} and {right_index + 1} overlapped"
                )


def assert_chart_width_ratio(
    card: Locator, diagnostics: E2EDiagnostics, label: str
) -> None:
    card_box = card.bounding_box()
    chart_box = card.locator("svg").first.bounding_box()
    if card_box is None or chart_box is None:
        raise AssertionError(f"{label} did not produce measurable card/chart bounds")
    ratio = chart_box["width"] / card_box["width"]
    diagnostics.record(f"[e2e] {label} chart/card width ratio={ratio:.3f}")
    if ratio < 0.85:
        raise AssertionError(
            f"{label} chart used only {ratio:.1%} of its result card width"
        )


def create_exports(page: Page) -> None:
    page.get_by_role("button", name="JSON 생성").click()
    expect(page.get_by_role("button", name="JSON 다운로드")).to_be_visible(
        timeout=15_000
    )

    page.get_by_role("button", name="CSV 생성").click()
    expect(page.get_by_role("button", name="CSV 다운로드")).to_be_visible(
        timeout=15_000
    )

    expect(page.get_by_text("최근 export")).to_be_visible()

    try:
        with page.expect_download(timeout=10_000) as download_info:
            page.get_by_role("button", name="JSON 다운로드").click()
        download = download_info.value
        if not download.suggested_filename.endswith(".json"):
            raise AssertionError(
                f"unexpected JSON download name: {download.suggested_filename}"
            )
    except PlaywrightTimeoutError as exc:
        raise AssertionError("JSON export download did not start") from exc

    export_items = page.locator(".export-list-item")
    expect(export_items).to_have_count(2, timeout=15_000)
    export_items.nth(0).get_by_role("button", name="삭제 영향 확인").click()
    deletion_impact = page.get_by_label("analysis export 삭제 영향")
    expect(deletion_impact).to_contain_text("파일 1개와 export metadata 1건")
    expect(deletion_impact).to_contain_text("분석 결과는 유지됩니다")
    deletion_impact.get_by_role("button", name="영구 삭제 확인").click()
    deletion_confirmation = page.get_by_label(
        "analysis export irreversible deletion 확인"
    )
    expect(deletion_confirmation).to_contain_text("복원할 수 없습니다")
    deletion_confirmation.get_by_role("button", name="export 영구 삭제").click()
    expect(page.get_by_text(re.compile(r"export 삭제 완료"))).to_be_visible(
        timeout=15_000
    )
    expect(export_items).to_have_count(1, timeout=15_000)
    expect(page.locator(".result-table").filter(has_text="Hedges g")).to_be_visible()


def verify_help_report_and_manage_routes(
    page: Page, diagnostics: E2EDiagnostics
) -> None:
    open_primary_navigation(page, "리포트")
    expect(page.get_by_role("heading", name="리포트 센터")).to_be_visible()
    expect_lazy_workspace_page(page, "ReportCenterPage")
    report_rows = page.locator(".report-run-row")
    expect(report_rows).to_have_count(2, timeout=20_000)
    report_rows.first.click()
    expect(page.get_by_role("heading", name="선택한 결과")).to_be_visible(
        timeout=15_000
    )
    expect(
        report_rows.first.locator("xpath=..").locator(".report-selected-result")
    ).to_be_visible()
    expect(page.get_by_role("button", name="HTML 생성")).to_be_enabled()
    expect(page.get_by_text("현재 지원되지 않음", exact=True).first).to_be_visible()
    page.get_by_role("button", name="HTML 생성").click()
    expect(page.get_by_role("button", name="HTML 다운로드")).to_be_visible(
        timeout=15_000
    )
    try:
        with page.expect_download(timeout=10_000) as download_info:
            page.get_by_role("button", name="HTML 다운로드").click()
        if not download_info.value.suggested_filename.endswith(".html"):
            raise AssertionError("unexpected Report Center HTML filename")
    except PlaywrightTimeoutError as exc:
        raise AssertionError("Report Center HTML download did not start") from exc
    page.reload(wait_until="networkidle")
    expect(page.get_by_role("heading", name="리포트 센터")).to_be_visible(
        timeout=15_000
    )

    open_primary_navigation(page, "도움말")
    expect(page.get_by_role("heading", name="도움말", exact=True)).to_be_visible()
    expect_lazy_workspace_page(page, "HelpCenterPage")
    expect(page.get_by_text("무엇을 알고 싶나요?")).to_be_visible()
    expect(page.get_by_role("heading", name="변수 역할 사전")).to_be_visible()
    page.get_by_role("button", name="그래프 요약 메서드 보기").click()
    expect(page.get_by_role("heading", name="그래프 요약", exact=True)).to_be_focused()
    expect(page).to_have_url(re.compile(r"[?&]method_id=eda\.graphical_summary"))
    page.reload(wait_until="networkidle")
    expect(page.get_by_role("heading", name="도움말", exact=True)).to_be_visible(
        timeout=15_000
    )

    expect(
        page.get_by_role("heading", name="Statistical Twin", exact=True)
    ).to_be_visible()
    open_primary_navigation(page, "홈")
    expect(page).to_have_url(re.compile(r"/home(?:\?|$)"))
    expect(page.get_by_role("button", name="홈", exact=True)).to_have_attribute(
        "aria-current", "page"
    )
    expect(
        page.get_by_role("heading", name="Statistical Twin 대시보드", exact=True)
    ).to_be_visible(timeout=15_000)
    expect_lazy_workspace_page(page, "ProjectOverviewPage")
    expect(
        page.get_by_text(
            "로컬 작업공간의 최근 자산을 확인하고 다음 작업을 시작합니다.",
            exact=True,
        )
    ).to_be_visible()
    page.reload(wait_until="networkidle")
    expect(
        page.get_by_role("heading", name="Statistical Twin 대시보드", exact=True)
    ).to_be_visible(timeout=15_000)

    open_primary_navigation(page, "관리")
    expect(page.get_by_role("heading", name="자산 관리")).to_be_visible(timeout=15_000)
    expect_lazy_workspace_page(page, "ManageAssetsPage")
    asset_table = page.locator(".asset-catalog-table")
    expect(asset_table).to_be_visible()
    expect(asset_table.get_by_role("columnheader", name="종류")).to_be_visible()
    expect(page.locator(".asset-filter-table")).to_be_visible()
    expect(page.locator(".asset-catalog-detail")).to_have_count(0)
    pinned_label = page.locator(".asset-filter-table .doe-table-toggle")
    pinned_label_box = pinned_label.bounding_box()
    pinned_checkbox_box = pinned_label.locator('input[type="checkbox"]').bounding_box()
    pinned_text_box = pinned_label.locator("span").bounding_box()
    pinned_cell_box = pinned_label.locator("xpath=ancestor::td").bounding_box()
    if (
        pinned_label_box is None
        or pinned_checkbox_box is None
        or pinned_text_box is None
        or pinned_cell_box is None
    ):
        raise AssertionError("asset pinned filter did not expose measurable bounds")
    expect(pinned_label).to_contain_text("고정만 보기")
    if pinned_text_box["x"] + pinned_text_box["width"] > (
        pinned_cell_box["x"] + pinned_cell_box["width"] + 1
    ):
        raise AssertionError("asset pinned filter escaped its table cell")
    if pinned_checkbox_box["x"] + pinned_checkbox_box["width"] > pinned_text_box["x"]:
        raise AssertionError("asset pinned checkbox overlapped its label")
    diagnostics.capture_page(page, "asset-filter-table.png")
    diagnostics.capture_page(page, "asset-management-overview.png")
    detail_button = page.get_by_role("button", name="상세", exact=True).first
    detail_button_id = detail_button.get_attribute("id")
    if detail_button_id is None:
        raise AssertionError("asset detail button did not expose a stable id")
    detail_button.click()
    expect(page.locator(".asset-catalog-detail")).to_be_visible()
    inline_position_is_valid = page.locator(f"#{detail_button_id}").evaluate(
        """
        (button) => {
          const assetRow = button.closest('tr');
          const detailRow = assetRow?.nextElementSibling;
          return detailRow?.matches('tr.asset-inline-detail-row') ?? false;
        }
        """
    )
    if not inline_position_is_valid:
        raise AssertionError("asset detail row was not rendered after the selected row")
    diagnostics.capture_page(page, "asset-inline-detail.png")
    diagnostics.capture_page(page, "asset-management-detail.png")
    page.reload(wait_until="networkidle")
    expect(page.get_by_role("heading", name="자산 관리")).to_be_visible(timeout=15_000)

    open_primary_navigation(page, "분석")
    help_trigger = page.get_by_role("button", name="분석 도움말")
    expect(help_trigger).to_be_visible()
    help_trigger.click()
    help_drawer = page.locator("#method-help-drawer")
    expect(help_drawer).to_be_visible()
    expect(
        help_drawer.get_by_role("heading", name="사전점검과 결과 해석")
    ).to_be_visible()
    expect(help_drawer.get_by_text("결과에서 먼저 볼 값", exact=True)).to_be_visible()
    page.keyboard.press("Escape")
    expect(help_drawer).to_have_count(0)
    expect(help_trigger).to_be_focused()


def verify_reporting_summary_variance_and_scatter(
    page: Page,
    diagnostics: E2EDiagnostics,
) -> None:
    open_primary_navigation(page, "데이터셋")
    paste_plain_text(page, REPORTING_SUMMARY_DATA)
    page.get_by_role("button", name="붙여넣기 데이터 등록").click()
    expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
    page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
    expect(page.locator("#version-title")).to_contain_text("v1", timeout=20_000)

    open_primary_navigation(page, "그래프")
    expect(page.get_by_role("heading", name="그래프 작성")).to_be_visible()
    page.wait_for_timeout(750)
    page.locator(".graph-type-button").filter(
        has_text=re.compile("^Scatter Plot")
    ).click()
    page.get_by_role("radio", name="Y 1개 · X 여러 개").check()
    expect(page.get_by_role("radio", name="Y 1개 · X 여러 개")).to_be_checked()
    page.locator(".graph-role-option").filter(has_text="고정 Y 변수").locator(
        "select"
    ).select_option(label="yield_pct")
    x_picker = page.locator(".graph-variable-picker").filter(
        has_text=re.compile("^X 변수")
    )
    for label in ("temperature_c", "pressure_bar"):
        checkbox = x_picker.get_by_role("checkbox", name=re.compile(rf"^{label}"))
        if not checkbox.is_checked():
            checkbox.check()
    create_button = page.get_by_role("button", name="그래프 생성", exact=True)
    expect(create_button).to_be_enabled()
    create_button.click()
    expect(page.get_by_role("heading", name="그래프 결과")).to_be_visible(
        timeout=20_000
    )
    expect(page.locator(".graph-preview-grid-scatter-plot > article")).to_have_count(2)
    expect(
        page.get_by_role("heading", name="yield_pct vs temperature_c")
    ).to_be_visible()
    expect(
        page.get_by_role("heading", name="yield_pct vs pressure_bar")
    ).to_be_visible()
    diagnostics.capture_page(page, "scatter-fixed-y-multiple-x.png")

    open_primary_navigation(page, "분석")
    select_method_card(page, "탐색적 분석", "그래프 요약")
    picker = page.get_by_label("그래프 요약 컬럼 선택")
    for checkbox in picker.get_by_role("checkbox").all():
        if checkbox.is_checked():
            checkbox.uncheck()
    picker.get_by_role("checkbox", name=re.compile(r"^yield_pct")).check()
    page.get_by_role("button", name="그래프 요약 실행").click()
    summary = page.get_by_label("yield_pct 그래프 요약")
    expect(summary).to_be_visible(timeout=20_000)
    expect(summary.get_by_text("Anderson-Darling 정규성 검정")).to_be_visible()
    expect(summary.get_by_text("히스토그램 + 적합 정규곡선")).to_be_visible()
    expect(summary.get_by_text("박스플롯", exact=True)).to_be_visible()
    expect(summary.get_by_text("Q-Q Plot", exact=True)).to_be_visible()
    expect(summary.get_by_role("img", name="yield_pct 신뢰구간")).to_be_visible()
    diagnostics.capture_page(page, "graphical-summary-minitab-layout.png")
    page.set_viewport_size({"width": 390, "height": 844})
    if (
        page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
        > 1
    ):
        raise AssertionError("graphical summary overflowed the mobile viewport")
    diagnostics.capture_page(page, "graphical-summary-mobile.png")
    page.set_viewport_size({"width": 1440, "height": 900})

    select_method_card(page, "탐색적 분석", "등분산 검정")
    diagnostics.record("[e2e] equal variances method selected")
    equal_variances_panel = page.locator(
        '[data-analysis-execution="eda.equal_variances"]'
    )
    expect(equal_variances_panel).to_be_visible(timeout=15_000)
    diagnostics.record("[e2e] equal variances panel visible")
    page.wait_for_timeout(500)
    select_option_by_label_without_retry(
        equal_variances_panel.locator("select").nth(0), "yield_pct"
    )
    diagnostics.record("[e2e] equal variances response selected")
    select_option_by_label_without_retry(
        equal_variances_panel.locator("select").nth(1), "production_line"
    )
    diagnostics.record("[e2e] equal variances group selected")
    equal_variances_button = equal_variances_panel.get_by_role(
        "button", name="등분산 검정 실행"
    )
    expect(equal_variances_button).to_be_enabled()
    diagnostics.record("[e2e] equal variances button enabled")
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and response.url.endswith("/api/v1/analysis-runs"),
        timeout=20_000,
    ) as equal_variances_response_info:
        equal_variances_button.focus()
        expect(equal_variances_button).to_be_focused()
        page.keyboard.press("Enter")
    equal_variances_payload = equal_variances_response_info.value.json()
    if equal_variances_payload.get("method_id") != "eda.equal_variances":
        raise AssertionError("equal variances response used the wrong method")
    equal_variances_result = equal_variances_payload.get("result", {})
    if equal_variances_result.get("schema_version") != 2:
        raise AssertionError("equal variances response did not use result schema 2")
    diagnostics.record(
        "[e2e] equal variances response received; "
        f"result keys={sorted(equal_variances_result.keys())}"
    )
    expect(page.locator(".equal-variances-method-table")).to_contain_text(
        "다중 비교", timeout=20_000
    )
    expect(page.locator(".equal-variances-method-table")).to_contain_text("Levene 검정")
    interval_chart = page.get_by_role(
        "img", name="등분산 검정: yield_pct 대 production_line"
    )
    expect(interval_chart).to_be_visible()
    interval_chart.locator(".variance-comparison-group").first.focus()
    expect(
        page.locator(".variance-comparison-chart .chart-selected-detail")
    ).to_contain_text("표본 표준편차")
    diagnostics.capture_page(page, "equal-variances-intervals.png")

    select_method_card(page, "탐색적 분석", "그래프 요약")
    page.get_by_role("button", name="그래프 요약 실행").click()
    expect(page.get_by_label("yield_pct 그래프 요약")).to_be_visible(timeout=20_000)
    open_primary_navigation(page, "리포트")
    report_rows = page.locator(".report-run-row")
    expect(report_rows).not_to_have_count(0, timeout=20_000)
    report_rows.first.click()
    page.get_by_role("button", name="HTML 생성").click()
    expect(page.get_by_role("button", name="HTML 다운로드")).to_be_visible(
        timeout=15_000
    )
    with page.expect_download(timeout=15_000) as download_info:
        page.get_by_role("button", name="HTML 다운로드").click()
    download = download_info.value
    if not download.suggested_filename.startswith("statistical-twin-"):
        raise AssertionError(
            f"unexpected HTML report filename: {download.suggested_filename}"
        )
    report_path = Path(download.path())
    report_text = report_path.read_text(encoding="utf-8")
    for expected in (
        "Statistical Twin 분석 보고서",
        '<html lang="ko">',
        "핵심 결과",
        "그래프",
        "<svg",
        "기술 정보",
    ):
        if expected not in report_text:
            raise AssertionError(f"HTML report did not contain {expected!r}")
    if "<script" in report_text.lower():
        raise AssertionError("HTML report contained a script element")
    report_page = page.context.new_page()
    try:
        # Playwright download temp paths do not preserve the .html suffix, so a
        # file: navigation can be served as plain text despite valid HTML.
        report_page.set_content(report_text, wait_until="load")
        expect(
            report_page.get_by_role("heading", name=re.compile("결과 보고서"))
        ).to_be_visible()
        diagnostics.capture_page(report_page, "html-report-graphical-summary.png")
    finally:
        report_page.close()


def verify_descriptive_quick_charts_and_run_chart(page: Page) -> None:
    open_primary_navigation(page, "데이터셋")
    paste_plain_text(page, SAMPLE_DATA)
    page.get_by_role("button", name="붙여넣기 데이터 등록").click()
    expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
    page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
    expect(page.locator("#version-title")).to_contain_text("v1", timeout=20_000)
    expect(page.locator(".active-dataset-summary")).to_contain_text("생성")

    open_primary_navigation(page, "분석")
    select_method_card(page, "탐색적 분석", "기술통계")
    page.get_by_role("button", name="기술통계 실행").click()
    expect(page.get_by_role("button", name="Value 그래프 보기")).to_be_visible(
        timeout=20_000
    )
    page.get_by_role("button", name="Value 그래프 보기").click()
    quick_graph = page.get_by_label("Value 그래프 요약")
    expect(quick_graph).to_be_visible(timeout=20_000)
    expect(quick_graph.get_by_text("히스토그램", exact=True)).to_be_visible()
    expect(quick_graph.get_by_text("박스플롯", exact=True)).to_be_visible()
    marker_labels = quick_graph.locator("text.boxplot-value-label")
    expect(marker_labels).to_have_count(5)
    for index in range(5):
        expect(marker_labels.nth(index)).to_have_text(re.compile(r"^-?[\d,.]+$"))

    select_method_card(page, "품질 관리", "런 차트")
    page.get_by_label("측정값").select_option(label="Value")
    page.get_by_role("button", name="런 차트 실행").click()
    randomness_section = page.get_by_role("region", name="근사 랜덤성 검정")
    expect(randomness_section).to_be_visible(timeout=20_000)
    for label in ("군집", "혼합", "추세", "진동"):
        expect(
            randomness_section.locator(".metric-card").filter(has_text=label)
        ).to_be_visible()


def restore_and_compare_saved_results(page: Page) -> None:
    compact_history = page.locator(".compact-analysis-history")
    expect(compact_history.get_by_text("저장된 분석 이력", exact=True)).to_be_visible()
    expect(page.locator(".analysis-history-item")).to_have_count(0)
    compact_history.get_by_role("button", name="최근 이력 열기").click()
    expect(page.locator(".compact-history-list article")).to_have_count(
        1, timeout=20_000
    )
    compact_history.get_by_role("link", name="전체 이력 관리").click()
    expect(page.get_by_role("heading", name="리포트 센터")).to_be_visible(
        timeout=15_000
    )
    expect(page.get_by_role("heading", name="전체 분석 이력")).to_be_visible(
        timeout=15_000
    )
    page.locator(".analysis-history-controls").get_by_label("method").select_option("")
    history_items = page.locator(".analysis-history-item")
    expect(history_items).to_have_count(2, timeout=20_000)

    history_items.nth(0).get_by_role("button", name="결과 불러오기").click()
    expect(page.locator("#workbench-title")).to_have_text(
        "2-표본 t-검정", timeout=15_000
    )

    open_primary_navigation(page, "리포트")
    expect(page.get_by_role("heading", name="리포트 센터")).to_be_visible(
        timeout=15_000
    )
    page.get_by_role("tab", name="분석 이력").click()
    expect(page.get_by_role("heading", name="전체 분석 이력")).to_be_visible(
        timeout=15_000
    )
    page.locator(".analysis-history-controls").get_by_label("method").select_option("")
    history_items = page.locator(".analysis-history-item")
    expect(history_items).to_have_count(2, timeout=20_000)

    history_items.nth(0).get_by_role("button", name="왼쪽").click()
    history_items.nth(1).get_by_role("button", name="오른쪽").click()
    page.get_by_role("button", name="비교").click()
    expect(page.get_by_text("비교 결과")).to_be_visible(timeout=15_000)
    expect(
        page.get_by_text("같은 method/version일 때만 자세한 비교가 가능합니다.")
    ).to_be_visible()
    expect(page.get_by_text(re.compile(r"method (same|different)"))).to_be_visible()


def delete_one_saved_analysis_run(page: Page) -> None:
    history_items = page.locator(".analysis-history-item")
    expect(history_items).to_have_count(2, timeout=15_000)

    history_items.nth(1).get_by_role("button", name="삭제 영향 확인").click()
    deletion_impact = page.get_by_label("analysis run 삭제 영향")
    expect(deletion_impact).to_contain_text("파일 2개", timeout=15_000)
    expect(deletion_impact).to_contain_text("export 0개")
    deletion_impact.get_by_role("button", name="영구 삭제 확인").click()
    deletion_confirmation = page.get_by_label("analysis run irreversible deletion 확인")
    expect(deletion_confirmation).to_contain_text("복원할 수 없습니다")
    deletion_confirmation.get_by_role("button", name="분석 실행 영구 삭제").click()

    expect(page.get_by_text(re.compile(r"분석 실행 삭제 완료"))).to_be_visible(
        timeout=15_000
    )
    expect(history_items).to_have_count(1, timeout=15_000)
    expect(page.get_by_text("불러온 결과")).to_have_count(1)
    expect(page.get_by_text("비교 결과")).to_have_count(0)


def verify_schema_stale_behavior(page: Page) -> None:
    open_primary_navigation(page, "데이터셋")
    expect(page.locator("#version-title")).to_contain_text("v2", timeout=15_000)

    page.get_by_role("button", name="스키마 저장").click()
    expect(page.get_by_role("button", name="스키마 저장")).to_be_enabled(timeout=15_000)

    open_primary_navigation(page, "분석")
    select_method_card(page, "가설 검정", "2-표본 t-검정")
    compact_history = page.locator(".compact-analysis-history")
    compact_history.get_by_role("button", name="최근 이력 열기").click()
    expect(page.locator(".compact-history-list article")).to_have_count(
        1, timeout=15_000
    )
    expect(page.locator(".compact-history-list .stale-badge")).to_have_count(0)

    open_primary_navigation(page, "데이터셋")
    value_display_input = page.get_by_label("Value 표시명")
    value_display_input.fill("Measurement Value")
    page.get_by_role("button", name="스키마 저장").click()
    expect(value_display_input).to_have_value("Measurement Value", timeout=15_000)

    open_primary_navigation(page, "분석")
    select_method_card(page, "가설 검정", "2-표본 t-검정")
    compact_history = page.locator(".compact-analysis-history")
    compact_history.get_by_role("button", name="최근 이력 열기").click()
    expect(page.locator(".compact-history-list article")).to_have_count(
        1, timeout=15_000
    )
    expect(page.locator(".compact-history-list .stale-badge")).to_have_count(1)
    expect(page.get_by_text("stale", exact=True).first).to_be_visible()


def verify_linear_model_fit_and_prediction(
    page: Page, diagnostics: E2EDiagnostics
) -> None:
    open_primary_navigation(page, "데이터셋")
    paste_plain_text(page, REGRESSION_TARGET_DATA)
    page.get_by_role("button", name="붙여넣기 데이터 등록").click()
    expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and response.url.endswith("/confirm-parsing")
    ) as target_confirm_info:
        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
    target_active_version_id = target_confirm_info.value.json()["version_id"]
    expect_dataset_context_counts(page, row_label="4행", column_label="3컬럼")
    active_dataset_selector = page.locator("#active-dataset-version")
    expect(active_dataset_selector).to_be_enabled(timeout=15_000)
    expect(active_dataset_selector).to_have_value(target_active_version_id)

    paste_plain_text(page, REGRESSION_SAMPLE_DATA)
    page.get_by_role("button", name="붙여넣기 데이터 등록").click()
    expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)

    with page.expect_response(
        lambda response: response.request.method == "POST"
        and response.url.endswith("/confirm-parsing")
    ) as training_confirm_info:
        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
    training_active_version_id = training_confirm_info.value.json()["version_id"]
    expect_dataset_context_counts(page, row_label="12행", column_label="3컬럼")
    expect(active_dataset_selector).to_have_value(training_active_version_id)
    page.get_by_label("afucose 측정 수준").select_option("continuous")
    page.get_by_label("afucose 역할").select_option("factor")
    page.get_by_label("adcc 측정 수준").select_option("continuous")
    page.get_by_label("adcc 역할").select_option("response")
    with page.expect_response(
        lambda response: response.request.method == "PATCH"
        and response.url.endswith("/schema")
    ):
        page.get_by_role("button", name="스키마 저장").click()
    expect(page.get_by_label("afucose 역할")).to_have_value("factor")
    expect(page.get_by_label("adcc 역할")).to_have_value("response")
    open_primary_navigation(page, "분석")
    select_method_card(page, "상관관계 및 회귀분석", "회귀모형 적합")
    expect(page.locator("#workbench-title")).to_have_text("회귀모형 적합")
    expect_lazy_analysis_module(page, "RegressionAnalysisPanels")

    page.get_by_label("반응 변수").select_option(label="adcc")
    predictor_options = page.get_by_label("예측변수")
    x_predictor = predictor_options.get_by_role(
        "checkbox", name=re.compile(r"^afucose")
    )
    group_predictor = predictor_options.get_by_role(
        "checkbox",
        name=re.compile(r"^group"),
    )
    x_predictor.check()
    expect(x_predictor).to_be_checked()
    expect(predictor_options).to_contain_text("숫자형 · 연속 · 요인 역할")
    expect(
        page.get_by_label("숫자형 2차항").get_by_role(
            "checkbox", name=re.compile(r"^afucose")
        )
    ).to_be_visible()
    expect(group_predictor).to_be_checked()

    with page.expect_response(
        lambda response: response.request.method == "POST"
        and response.url.endswith("/api/v1/analysis-runs")
    ) as model_response_info:
        page.get_by_role("button", name="회귀모형 적합 실행").click()
    model_response = model_response_info.value
    model_id = model_response.json()["result"]["model_manifest"]["model_id"]
    model_summary = page.get_by_label("회귀 모델 요약")
    expect(model_summary).to_be_visible(timeout=20_000)
    expect(model_summary).to_contain_text("Predicted R²")
    expect(model_summary).to_contain_text("PRESS")
    expect(model_summary).to_contain_text("최대 VIF")
    expect(page.get_by_role("heading", name="회귀방정식")).to_be_visible()
    expect(page.locator(".linear-model-equation")).to_contain_text("adcc")
    expect(page.locator(".linear-model-equation")).to_contain_text("afucose")
    expect(page.get_by_role("heading", name="분산분석")).to_be_visible()
    anova_table = page.locator(".result-table").filter(has_text="Adj SS")
    expect(anova_table).to_be_visible()
    expect(anova_table).to_contain_text("Regression")
    page.get_by_role("button", name="4-in-1 잔차 그림 보기").click()
    expect(page.get_by_text("잔차 정규확률도", exact=True)).to_be_visible()
    expect(page.get_by_text("잔차 히스토그램", exact=True)).to_be_visible()
    expect(page.get_by_text("잔차 대 적합값", exact=True)).to_be_visible()
    expect(page.get_by_text("잔차 대 관측순서", exact=True)).to_be_visible()
    expect(page.locator(".linear-model-four-in-one .chart-panel")).to_have_count(4)
    diagnostics.capture_page(page, "regression-four-in-one.png")
    observed_chart = page.locator(".chart-panel").filter(has_text="Observed vs Fitted")
    expect(observed_chart).to_be_visible()
    expect(observed_chart.locator(".reference-line")).to_have_count(1)
    observed_point = observed_chart.locator(".diagnostic-point").first
    observed_point.hover()
    expect(observed_chart.locator(".chart-selected-detail")).to_contain_text("실제값")
    observed_point.focus()
    expect(observed_point).to_have_attribute("data-selected", "true")
    expect(
        page.locator(".chart-panel").filter(has_text="Leverage vs Cook's D")
    ).to_be_visible()
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and response.url.endswith("/response-optimizations")
    ) as optimizer_response_info:
        page.get_by_role("button", name="반응 최적화 실행").click()
    optimizer_response = optimizer_response_info.value
    optimizer_id = optimizer_response.json()["optimization_id"]
    optimizer_summary = page.get_by_label("회귀 반응 최적화 결과")
    expect(optimizer_summary).to_be_visible(timeout=20_000)
    expect(optimizer_summary).to_contain_text("범위 안")
    expect(page.get_by_text("확인 실험이 필요합니다", exact=False)).to_be_visible()
    profiles = page.locator(".regression-optimizer-profile-card")
    expect(profiles).to_have_count(2)
    assert_children_do_not_overlap(
        page.locator(".regression-optimizer-profile-grid"),
        profiles,
        "regression optimizer profiles",
    )
    expect(page.locator(".regression-categorical-profile-table-wrap")).to_have_count(1)
    diagnostics.capture_page(page, "regression-optimizer-profile-layout.png")

    manual_prediction = page.locator(".regression-manual-prediction")
    expect(
        manual_prediction.get_by_role("heading", name="예측 조건 입력")
    ).to_be_visible()
    expect(manual_prediction.get_by_label("예측 대상 데이터셋 버전")).to_have_count(0)
    manual_prediction.get_by_role("button", name="붙여넣기 가져오기").click()
    manual_prediction.get_by_label("예측 조건 붙여넣기").fill("1\tA")
    manual_prediction.get_by_label("첫 행에 열 이름 포함").check()
    manual_prediction.get_by_role("button", name="입력 grid에 적용").click()
    expect(manual_prediction.get_by_role("alert")).to_contain_text(
        "실제 예측 데이터 행이 없습니다"
    )
    diagnostics.capture_page(page, "regression-one-row-header-warning.png")
    manual_prediction.get_by_label("첫 행에 열 이름 포함").uncheck()
    manual_prediction.get_by_role("button", name="입력 grid에 적용").click()
    expect(manual_prediction.get_by_label("1행 afucose")).to_have_value("1")
    expect(manual_prediction.get_by_label("1행 group")).to_have_value("A")
    manual_prediction.get_by_role("button", name="붙여넣기 가져오기").click()
    manual_prediction.get_by_label("예측 조건 붙여넣기").fill(
        "afucose\tgroup\n1\tA\n3.5\tB\n5.5\tC"
    )
    manual_prediction.get_by_label("첫 행에 열 이름 포함").check()
    manual_prediction.get_by_role("button", name="입력 grid에 적용").click()
    expect(manual_prediction.locator(".regression-manual-grid tbody tr")).to_have_count(
        3
    )
    diagnostics.capture_page(page, "regression-manual-input-grid.png")
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and response.url.endswith("/pasted-prediction-preflight")
    ):
        manual_prediction.get_by_role("button", name="전체 사전점검").click()
    expect(manual_prediction.get_by_role("status")).to_contain_text(
        "사용 가능 3 / 전체 3행", timeout=20_000
    )
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and response.url.endswith("/pasted-predictions")
    ) as prediction_response_info:
        manual_prediction.get_by_role("button", name="전체 예측 실행").click()
    prediction_id = prediction_response_info.value.json()["prediction_id"]
    expect(manual_prediction.get_by_role("heading", name="예측 결과")).to_be_visible(
        timeout=20_000
    )
    manual_table = manual_prediction.locator(".result-table").filter(
        has_text="개별 예측구간"
    )
    expect(manual_table.locator("tbody tr")).to_have_count(3)
    expect(manual_table).to_have_class(re.compile(r"is-summary"))
    summary_headers = manual_table.locator("thead th")
    for label in ("예측 평균", "평균 신뢰구간", "개별 예측구간", "상태"):
        header = summary_headers.filter(has_text=re.compile(rf"^{re.escape(label)}$"))
        expect(header).to_have_count(1)
        box = header.bounding_box()
        if box is None or box["width"] < 105:
            raise AssertionError(
                f"prediction summary header {label} was too narrow: {box}"
            )
    diagnostics.capture_page(page, "regression-prediction-summary-table.png")
    manual_prediction.get_by_role("button", name="입력값 포함").click()
    full_table = manual_prediction.locator(
        ".regression-prediction-results-table.is-full"
    )
    expect(full_table).to_be_visible()
    expect(full_table.get_by_role("columnheader", name="입력 조건")).to_be_visible()
    expect(full_table.get_by_role("columnheader", name="예측 결과")).to_be_visible()
    results_wrap = manual_prediction.locator(".regression-prediction-results-wrap")
    if results_wrap.evaluate("element => getComputedStyle(element).overflowX") not in {
        "auto",
        "scroll",
    }:
        raise AssertionError(
            "prediction result wrapper did not own horizontal overflow"
        )
    page_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    if page_overflow > 1:
        raise AssertionError(f"prediction table caused {page_overflow}px page overflow")
    diagnostics.capture_page(page, "regression-prediction-full-table.png")

    frontend_base_url = page.url.split("/analysis", 1)[0]
    dedicated_page = page.context.new_page()
    dedicated_prediction_id: str | None = None
    try:
        dedicated_page.goto(
            f"{frontend_base_url}/analysis/regression/regression.predict",
            wait_until="networkidle",
        )
        expect(dedicated_page.locator("#workbench-title")).to_have_text(
            "예측", timeout=20_000
        )
        expect(
            dedicated_page.locator(".workbench-heading .availability-badge")
        ).to_have_text("사용 가능 · 전용 워크플로")
        dedicated_model_selector = dedicated_page.get_by_label("Source 회귀모형")
        expect(
            dedicated_model_selector.locator(f'option[value="{model_id}"]')
        ).to_have_count(
            1,
            timeout=20_000,
        )
        dedicated_model_selector.select_option(model_id)
        dedicated_target_selector = dedicated_page.get_by_label(
            "예측 대상 데이터셋 버전"
        )
        expect(dedicated_target_selector).to_be_enabled(timeout=20_000)
        dedicated_target_selector.select_option(target_active_version_id)
        dedicated_page.get_by_role("button", name="예측 사전점검").click()
        expect(
            dedicated_page.get_by_role("heading", name="예측 사전점검 결과")
        ).to_be_visible(timeout=20_000)
        with dedicated_page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/predictions")
        ) as dedicated_prediction_response_info:
            dedicated_page.get_by_role("button", name="예측 실행").click()
        dedicated_prediction_response = dedicated_prediction_response_info.value
        dedicated_prediction_id = dedicated_prediction_response.json()["prediction_id"]
        expect(dedicated_page.get_by_role("heading", name="예측 결과")).to_be_visible(
            timeout=20_000
        )
        dedicated_table = dedicated_page.locator(".result-table").filter(
            has_text="개별 예측구간"
        )
        expect(dedicated_table.locator("tbody tr")).to_have_count(4)
        dedicated_page.get_by_role("button", name="전체 예측 CSV 생성").click()
        expect(
            dedicated_page.get_by_role("button", name="전체 예측 CSV 다운로드")
        ).to_be_visible(timeout=15_000)
        expect(dedicated_page).to_have_url(re.compile(f"model_id={model_id}"))
        expect(dedicated_page).to_have_url(
            re.compile(f"target_version_id={target_active_version_id}")
        )
        expect(dedicated_page).to_have_url(
            re.compile(f"prediction_id={dedicated_prediction_id}")
        )
        expect(dedicated_page.get_by_role("heading", name="분석 이력")).to_have_count(0)
        expect(
            dedicated_page.get_by_role("heading", name="결과 내보내기")
        ).to_have_count(0)

        dedicated_page.reload(wait_until="networkidle")
        expect(dedicated_page.get_by_label("Source 회귀모형")).to_have_value(
            model_id,
            timeout=20_000,
        )
        expect(dedicated_page.get_by_label("예측 대상 데이터셋 버전")).to_have_value(
            target_active_version_id,
            timeout=20_000,
        )
        expect(dedicated_page.get_by_label("선택한 회귀모형 metadata")).to_be_visible()
        expect(dedicated_page.get_by_role("heading", name="예측 결과")).to_be_visible(
            timeout=20_000
        )
        restored_table = dedicated_page.locator(".result-table").filter(
            has_text="개별 예측구간"
        )
        expect(restored_table.locator("tbody tr")).to_have_count(4)
        restored_export_button = dedicated_page.get_by_role(
            "button", name="전체 예측 CSV 생성"
        )
        expect(restored_export_button).to_be_enabled(timeout=15_000)
    finally:
        if dedicated_prediction_id is not None:
            api_v1 = model_response.url.rsplit("/analysis-runs", 1)[0]
            dedicated_delete_preflight = dedicated_page.request.get(
                f"{api_v1}/analysis-runs/{dedicated_prediction_id}/deletion-preflight"
            )
            if not dedicated_delete_preflight.ok:
                raise AssertionError(
                    "dedicated prediction deletion preflight failed: "
                    + dedicated_delete_preflight.text()
                )
            dedicated_delete_manifest = dedicated_delete_preflight.json()
            dedicated_delete = dedicated_page.request.delete(
                f"{api_v1}/analysis-runs/{dedicated_prediction_id}/deletion",
                data={
                    "confirmation_analysis_id": dedicated_prediction_id,
                    "expected_deletion_manifest_sha256": dedicated_delete_manifest[
                        "deletion_manifest_sha256"
                    ],
                },
            )
            if not dedicated_delete.ok:
                raise AssertionError(
                    f"dedicated prediction deletion failed: {dedicated_delete.text()}"
                )
        dedicated_page.close()

    api_v1 = model_response.url.rsplit("/analysis-runs", 1)[0]
    for owned_analysis_id in (optimizer_id,):
        owned_preflight = page.request.get(
            f"{api_v1}/analysis-runs/{owned_analysis_id}/deletion-preflight"
        )
        if not owned_preflight.ok:
            raise AssertionError(
                "owned regression result deletion preflight failed: "
                + owned_preflight.text()
            )
        owned_manifest = owned_preflight.json()
        owned_delete = page.request.delete(
            f"{api_v1}/analysis-runs/{owned_analysis_id}/deletion",
            data={
                "confirmation_analysis_id": owned_analysis_id,
                "expected_deletion_manifest_sha256": owned_manifest[
                    "deletion_manifest_sha256"
                ],
            },
        )
        if not owned_delete.ok:
            raise AssertionError(
                f"owned regression result deletion failed: {owned_delete.text()}"
            )

    model_retention = page.get_by_role("region", name="저장 모델 관리")
    model_retention.get_by_role("button", name="삭제 영향 확인").click()
    expect(model_retention.get_by_text("예측 참조 0건", exact=True)).to_be_visible(
        timeout=15_000
    )
    expect(
        model_retention.get_by_text("붙여넣기 예측 1건", exact=False)
    ).to_be_visible()
    expect(
        model_retention.get_by_text(
            "종속 예측 결과를 먼저 삭제해야 모델을 삭제할 수 있습니다."
        )
    ).to_be_visible()
    expect(model_retention.get_by_role("button", name="모델 삭제")).to_be_disabled()

    prediction_delete_preflight = page.request.get(
        f"{api_v1}/analysis-runs/{prediction_id}/deletion-preflight"
    )
    if not prediction_delete_preflight.ok:
        raise AssertionError(
            "prediction deletion preflight failed: "
            + prediction_delete_preflight.text()
        )
    prediction_delete_manifest = prediction_delete_preflight.json()
    prediction_delete = page.request.delete(
        f"{api_v1}/analysis-runs/{prediction_id}/deletion",
        data={
            "confirmation_analysis_id": prediction_id,
            "expected_deletion_manifest_sha256": prediction_delete_manifest[
                "deletion_manifest_sha256"
            ],
        },
    )
    if not prediction_delete.ok:
        raise AssertionError(f"prediction deletion failed: {prediction_delete.text()}")

    model_retention.get_by_role("button", name="삭제 영향 확인").click()
    expect(model_retention.get_by_text("예측 참조 0건", exact=True)).to_be_visible(
        timeout=15_000
    )
    expect(
        model_retention.get_by_text("붙여넣기 예측 0건", exact=False)
    ).to_be_visible()
    model_retention.get_by_text(
        "이 모델로 새 예측을 실행할 수 없게 됨을 확인했습니다."
    ).click()
    model_retention.get_by_role("button", name="모델 삭제").click()
    unavailable_message = (
        "모형 적합 결과는 보존되어 있지만 예측용 모델 자산은 사용할 수 없습니다."
    )
    expect(model_retention.get_by_text(unavailable_message, exact=True)).to_be_visible(
        timeout=15_000
    )
    expect(model_summary).to_be_visible()
    expect(
        manual_prediction.get_by_role("button", name="전체 사전점검")
    ).to_be_disabled()
    expect(
        manual_prediction.get_by_role("button", name="전체 예측 실행")
    ).to_be_disabled()

    active_dataset_selector.select_option(target_active_version_id)
    expect_dataset_context_counts(page, row_label="4행", column_label="3컬럼")
    expect(page).to_have_url(
        re.compile(f"dataset_version_id={target_active_version_id}")
    )
    page.reload(wait_until="networkidle")
    expect(page.locator("#active-dataset-version")).to_have_value(
        target_active_version_id,
        timeout=20_000,
    )
    expect_dataset_context_counts(page, row_label="4행", column_label="3컬럼")
    page.locator("#active-dataset-version").select_option(training_active_version_id)
    expect_dataset_context_counts(page, row_label="12행", column_label="3컬럼")
    expect(page.get_by_role("button", name="전체 예측 CSV 생성")).to_have_count(0)

    page.reload(wait_until="networkidle")
    expect(page.locator("#workbench-title")).to_have_text(
        "회귀모형 적합", timeout=20_000
    )
    compact_history = page.locator(".compact-analysis-history")
    compact_history.get_by_role("button", name="최근 이력 열기").click()
    saved_linear_model = compact_history.locator(
        ".compact-history-list article"
    ).filter(has_text="regression.linear_model")
    expect(saved_linear_model).to_have_count(1, timeout=15_000)
    saved_linear_model.get_by_role("button", name="결과 불러오기").click()
    expect(page.get_by_label("회귀 모델 요약")).to_be_visible(timeout=15_000)
    restored_retention = page.get_by_role("region", name="저장 모델 관리")
    expect(
        restored_retention.get_by_text(unavailable_message, exact=True)
    ).to_be_visible(timeout=15_000)
    restored_manual_prediction = page.locator(".regression-manual-prediction")
    expect(
        restored_manual_prediction.get_by_text(
            "저장 모델을 사용할 수 없어 새 예측을 실행할 수 없습니다.",
            exact=True,
        )
    ).to_be_visible()
    expect(
        restored_manual_prediction.get_by_role("button", name="전체 사전점검")
    ).to_be_disabled()
    expect(
        restored_manual_prediction.get_by_role("button", name="전체 예측 실행")
    ).to_be_disabled()


def verify_attribute_control_chart(page: Page) -> None:
    open_primary_navigation(page, "데이터셋")
    paste_plain_text(page, ATTRIBUTE_CONTROL_BASELINE_DATA)
    page.get_by_role("button", name="붙여넣기 데이터 등록").click()
    expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
    page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
    expect_dataset_context_counts(page, row_label="20행", column_label="2컬럼")

    open_primary_navigation(page, "분석")
    select_method_card(page, "품질 관리", "계수형 관리도")
    expect(page.locator("#workbench-title")).to_have_text("계수형 관리도")
    expect_lazy_analysis_module(page, "QualityAnalysisPanels")
    expect(
        page.get_by_text("Phase I은 현재 데이터에서 기준선을 추정합니다", exact=False)
    ).to_be_visible()
    expect(page.get_by_role("radio", name="P", exact=True)).to_have_attribute(
        "aria-checked", "true"
    )
    expect(page.get_by_label("불량품 수")).to_have_value(re.compile(r".+"))
    expect(page.get_by_label("표본 크기")).to_have_value(re.compile(r".+"))

    with page.expect_response(
        lambda response: response.request.method == "POST"
        and response.url.endswith("/api/v1/analysis-runs")
    ) as baseline_response_info:
        page.get_by_role("button", name="P 관리도 실행").click()
    baseline_response = baseline_response_info.value
    baseline_payload = baseline_response.json()
    summary = page.get_by_label("계수형 관리도 요약")
    expect(summary).to_be_visible(timeout=20_000)
    expect(summary).to_contain_text("20 / 20")
    expect(summary).to_contain_text("Phase I")
    expect(summary).to_contain_text("필터 후 유효 관측에서 추정")
    api_v1 = baseline_response.url.rsplit("/analysis-runs", 1)[0]
    limit_set_response = page.request.post(
        f"{api_v1}/quality/attribute-control-limit-sets",
        data={"source_analysis_id": baseline_payload["analysis_id"]},
    )
    if not limit_set_response.ok:
        raise AssertionError(f"limit-set creation failed: {limit_set_response.text()}")

    select_method_card(page, "품질 관리", "I-MR 관리도")
    expect(page.locator("#workbench-title")).to_have_text("I-MR 관리도")
    page.get_by_label("측정값").select_option(label="defectives")
    page.get_by_role("button", name="I-MR 관리도 실행").click()
    expect(page.get_by_label("I-MR 관리도 요약")).to_be_visible(timeout=20_000)
    expect(page.get_by_label("I-MR 신호 요약")).to_be_visible()
    expect(page.get_by_text("I chart", exact=True)).to_be_visible()
    expect(page.get_by_text("MR chart", exact=True)).to_be_visible()
    expect(page.get_by_label("I-MR 관리도 해석 안내")).to_contain_text(
        "관리한계 안에 있다는 사실만으로"
    )
    expect(page.get_by_label("I-MR 관리도 해석 안내")).to_contain_text(
        "규격한계는 사용자가 정한 허용 기준"
    )

    open_primary_navigation(page, "데이터셋")
    paste_plain_text(page, ATTRIBUTE_CONTROL_CHART_DATA)
    page.get_by_role("button", name="붙여넣기 데이터 등록").click()
    expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
    page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
    expect_dataset_context_counts(page, row_label="1행", column_label="2컬럼")
    open_primary_navigation(page, "분석")
    select_method_card(page, "품질 관리", "계수형 관리도")
    page.get_by_role("radio", name="Phase II 고정 한계 모니터링").click()
    limit_set_select = page.get_by_label("검증된 limit set")
    expect(limit_set_select).to_be_enabled(timeout=20_000)
    limit_set_select.select_option(index=1)
    expect(page.get_by_text("호환성 확인 중...")).to_have_count(0, timeout=20_000)
    expect(
        page.get_by_text(
            "구조 호환성 확인 완료. 실제 행 값과 필터 결과는 실행 시 다시 검증됩니다.",
            exact=True,
        )
    ).to_be_visible()
    phase_2_button = page.get_by_role("button", name="P 관리도 실행")
    expect(phase_2_button).to_be_enabled(timeout=20_000)
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and response.url.endswith("/api/v1/analysis-runs")
    ) as phase_2_response_info:
        phase_2_button.click()
    phase_2_response = phase_2_response_info.value
    phase_2_payload = phase_2_response.json()
    expect(summary).to_be_visible(timeout=20_000)
    expect(summary).to_contain_text("1 / 1")
    expect(summary).to_contain_text("사용 불가 · 관측점 부족")
    expect(summary).to_contain_text("Phase II")
    expect(summary).to_contain_text("검증된 immutable limit set")
    expect(summary).to_contain_text("Limit set")
    expect(page.get_by_role("img", name=re.compile(r"P 관리도.*신호"))).to_be_visible()

    phase_2_analysis_id = phase_2_payload["analysis_id"]
    for export_kind in ("json", "csv", "html"):
        export_response = page.request.post(
            f"{api_v1}/analysis-runs/{phase_2_analysis_id}/exports/{export_kind}"
        )
        if not export_response.ok:
            raise AssertionError(
                f"Phase II {export_kind} export failed: {export_response.text()}"
            )

    compact_history = page.locator(".compact-analysis-history")
    compact_history.get_by_role("button", name="최근 이력 열기").click()
    stored_phase_2 = compact_history.locator(".compact-history-list article").filter(
        has_text="quality.attribute_control_chart"
    )
    expect(stored_phase_2).to_have_count(1, timeout=15_000)
    stored_phase_2.get_by_role("button", name="결과 불러오기").click()
    expect(summary).to_contain_text("1 / 1")
    expect(summary).to_contain_text("사용 불가 · 관측점 부족")

    page.get_by_role("button", name="limit set 삭제 영향 확인").click()
    expect(page.get_by_text("Phase II 참조 1건", exact=True)).to_be_visible(
        timeout=15_000
    )
    expect(
        page.get_by_text(
            "이 limit set을 참조하는 Phase II 분석을 먼저 삭제해야 합니다."
        )
    ).to_be_visible()
    expect(
        page.get_by_role("button", name="limit set 삭제", exact=True)
    ).to_be_disabled()


def verify_doe_factorial_analysis(page: Page, diagnostics: E2EDiagnostics) -> None:
    open_primary_navigation(page, "분석")
    select_method_card(page, "실험 계획법", "실험 계획 생성")
    expect(page.locator("#workbench-title")).to_have_text("실험 계획 생성")
    expect_lazy_analysis_module(page, "DoeAnalysisPanels")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    expect(page.locator(".doe-form-section")).to_have_count(0)
    factorial_root = page.locator(
        '.analysis-run-panel[data-analysis-execution="doe.factorial_design"]'
    )
    assert_doe_table_visual_consistency(factorial_root, diagnostics, "factorial")
    diagnostics.capture_page(page, "doe-factorial-table-ui.png")
    page.get_by_label("반복", exact=True).fill("2")
    page.get_by_label("센터점", exact=True).fill("1")
    page.locator("details.doe-advanced-settings > summary").click()
    page.get_by_label("실행 순서 무작위화", exact=True).uncheck()
    expect(page.get_by_label("반복", exact=True)).to_have_value("2")
    expect(page.get_by_text("예상 실험 9개", exact=True)).to_be_visible()
    create_design_button = page.get_by_role("button", name="DOE 설계 생성")
    expect(create_design_button).to_be_enabled()
    create_design_button.click()
    expect(page.get_by_text("2-level screening design", exact=True)).to_be_visible(
        timeout=20_000
    )
    expect(
        page.get_by_text("분석을 실행하면 현재 설계의 반응값이 잠깁니다.", exact=False)
    ).to_be_visible()

    for run_order in range(1, 10):
        page.get_by_label(f"run {run_order} response").fill(
            str(40 + run_order + (0.25 if run_order % 2 == 0 else -0.25))
        )
    page.get_by_role("button", name="반응값 저장").click()
    response_summary = page.get_by_label("저장된 DOE 반응 요약")
    expect(response_summary).to_be_visible(timeout=20_000)
    expect(response_summary).to_contain_text("Yield")
    expect(response_summary).to_contain_text("9")

    page.get_by_label("최대 상호작용 차수").select_option("2")
    page.get_by_role("button", name="효과 및 ANOVA 분석").click()
    expect(page.get_by_role("heading", name="Factorial 분석 결과")).to_be_visible(
        timeout=20_000
    )
    expect(page.get_by_role("img", name="절대 효과 순위 차트")).to_be_visible()
    expect(page.get_by_role("img", name="주효과 평균 차트")).to_be_visible()
    expect(page.get_by_role("columnheader", name="ANOVA source")).to_be_visible()
    expect(page.locator(".analysis-result-section")).to_contain_text("0.5.0")
    expect(page.get_by_label("DOE 잔차 진단 요약")).to_be_visible()
    expect(page.get_by_label("run 1 response")).to_be_disabled()
    expect(page.get_by_role("button", name="분석 후 반응 잠금")).to_be_disabled()
    expect(page.get_by_text("읽기 전용입니다", exact=False)).to_be_visible()
    page.get_by_role("button", name="새 revision으로 수정").click()
    expect(page.get_by_label("반응 이름")).to_be_disabled()
    expect(page.get_by_label("run 1 response")).to_be_enabled()
    expect(page.get_by_role("button", name="새 revision 저장")).to_be_enabled()

    page.reload(wait_until="networkidle")
    expect(page.locator("#workbench-title")).to_have_text("실험 계획 생성")
    page.get_by_role("radio", name="2수준 부분요인").check()
    page.get_by_label("반복", exact=True).fill("1")
    page.get_by_label("센터점", exact=True).fill("0")
    for _ in range(3):
        page.get_by_role("button", name="요인 추가", exact=True).click()
    page.get_by_label("검증된 부분요인 설계").select_option("5-factor-half-r5")
    diagnostics.capture_page(page, "factorial-design-type-selector.png")
    page.get_by_role("button", name="DOE 설계 생성").click()
    expect(page.get_by_text("Resolution", exact=True)).to_be_visible(timeout=20_000)
    expect(page.get_by_text("V", exact=True).first).to_be_visible()
    expect(page.get_by_role("columnheader", name="Alias group")).to_be_visible()
    diagnostics.capture_page(page, "fractional-factorial-alias.png")
    for run_order in range(1, 17):
        page.get_by_label(f"run {run_order} response").fill(
            str(50 + run_order + (run_order % 3) * 0.15)
        )
    with page.expect_response(
        lambda response: response.request.method == "PUT"
        and response.url.endswith("/responses")
    ):
        page.get_by_role("button", name="반응값 저장").click()
    page.get_by_role("button", name="효과 및 ANOVA 분석").click()
    expect(page.get_by_text("독립 효과가 아닙니다", exact=False)).to_be_visible(
        timeout=20_000
    )

    page.reload(wait_until="networkidle")
    expect(page.locator("#workbench-title")).to_have_text("실험 계획 생성")
    page.get_by_role("radio", name="일반 완전요인").check()
    page.get_by_role("button", name="요인 추가", exact=True).click()
    expect(page.get_by_text("예상 실험 수 27개", exact=False)).to_be_visible()
    page.get_by_role("button", name="일반 완전요인 설계 생성").click()
    expect(page.get_by_role("heading", name="일반 완전요인 설계")).to_be_visible(
        timeout=20_000
    )
    diagnostics.capture_page(page, "general-factorial-three-level.png")
    for run_order in range(1, 28):
        page.get_by_label(f"run {run_order} 반응").fill(
            str(70 + run_order * 0.4 + (run_order % 2) * 0.1)
        )
    with page.expect_response(
        lambda response: response.request.method == "PUT"
        and "/general-factorial/" in response.url
        and response.url.endswith("/responses")
    ):
        page.get_by_role("button", name="반응 저장", exact=True).click()
    page.get_by_role("button", name="일반 완전요인 ANOVA").click()
    expect(page.get_by_role("heading", name="분산분석")).to_be_visible(timeout=20_000)


def expect_lazy_analysis_module(page: Page, module_name: str) -> None:
    page.wait_for_function(
        """
        (expectedModule) => performance.getEntriesByType("resource").some(
          (entry) => entry.name.includes(expectedModule)
        )
        """,
        arg=module_name,
        timeout=10_000,
    )
    expect(page.get_by_label("분석 패널 로딩")).to_have_count(0)


def expect_lazy_workspace_page(page: Page, page_name: str) -> None:
    page.wait_for_function(
        """
        (expectedPage) => performance.getEntriesByType("resource").some(
          (entry) => entry.name.includes(expectedPage)
        )
        """,
        arg=page_name,
        timeout=10_000,
    )
    expect(page.get_by_label("페이지 로딩")).to_have_count(0)


def verify_lazy_panel_direct_routes(page: Page, frontend_base_url: str) -> None:
    routes = [
        (
            "/analysis/regression/regression.linear_model",
            "회귀모형 적합",
            "RegressionAnalysisPanels",
        ),
        (
            "/analysis/quality/quality.attribute_control_chart",
            "계수형 관리도",
            "QualityAnalysisPanels",
        ),
        (
            "/analysis/doe/doe.factorial_design",
            "실험 계획 생성",
            "DoeAnalysisPanels",
        ),
        (
            "/analysis/doe/doe.bayesian_optimization",
            "베이지안 최적화",
            "DoeAnalysisPanels",
        ),
    ]
    for route_path, heading, module_name in routes:
        page.goto(f"{frontend_base_url}{route_path}", wait_until="networkidle")
        expect(page.locator("#workbench-title")).to_have_text(heading, timeout=15_000)
        expect_lazy_analysis_module(page, module_name)
        expect(page.get_by_label("분석 패널 로드 오류")).to_have_count(0)


def verify_lazy_panel_error_boundary(
    context: BrowserContext,
    frontend_base_url: str,
) -> None:
    page = context.new_page()
    try:
        page.route("**/RegressionAnalysisPanels.ts*", lambda route: route.abort())
        page.goto(
            f"{frontend_base_url}/analysis/regression/regression.linear_model",
            wait_until="networkidle",
        )
        error_state = page.get_by_label("분석 패널 로드 오류")
        expect(error_state).to_be_visible(timeout=15_000)
        expect(error_state).to_contain_text("분석 화면을 불러오지 못했습니다.")
        expect(
            error_state.get_by_role("button", name="화면 다시 불러오기")
        ).to_be_visible()
        expect(page.locator("body")).not_to_contain_text(
            "Failed to fetch dynamically imported module"
        )
        page.unroute("**/RegressionAnalysisPanels.ts*")
        select_method_card(page, "실험 계획법", "실험 계획 생성")
        expect(page.locator("#workbench-title")).to_have_text(
            "실험 계획 생성", timeout=15_000
        )
        expect(page.get_by_label("분석 패널 로드 오류")).to_have_count(0)
    finally:
        page.close()


def verify_doe_response_surface_analysis(
    page: Page,
    diagnostics: E2EDiagnostics,
) -> None:
    select_method_card(page, "실험 계획법", "반응표면법")
    expect(page.locator("#workbench-title")).to_have_text("반응표면법")
    expect(page.locator(".doe-form-section")).to_have_count(0)
    rsm_root = page.locator(
        '.analysis-run-panel[aria-label="반응표면법 설계와 분석 입력"]'
    )
    assert_doe_table_visual_consistency(rsm_root, diagnostics, "response-surface")
    diagnostics.capture_page(page, "doe-rsm-table-ui.png")

    page.locator("details.doe-advanced-settings > summary").click()
    page.get_by_label("실행 순서 무작위화").uncheck()
    page.get_by_role("button", name="CCD 생성").click()
    expect(page.get_by_role("heading", name="CCD 실행표와 반응 입력")).to_be_visible(
        timeout=20_000
    )
    expect(
        page.get_by_text("분석을 실행하면 현재 설계의 반응값이 잠깁니다.", exact=False)
    ).to_be_visible()
    responses = [
        97.608745,
        95.220633,
        98.399868,
        96.011756,
        97.177787,
        98.321712,
        97.455212,
        94.044287,
        99.833687,
        99.574266,
        99.915654,
        99.749356,
        99.827037,
    ]
    for run_order, response in enumerate(responses, start=1):
        page.get_by_label(f"Run {run_order} 반응").fill(str(response))

    page.get_by_role("button", name="반응 저장").click()
    analysis_button = page.get_by_role("button", name="Quadratic model 적합")
    expect(analysis_button).to_be_enabled(timeout=20_000)
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and "/api/v1/doe-designs/response-surface/" in response.url
        and response.url.endswith("/analyses")
    ) as rsm_analysis_response_info:
        analysis_button.click()
    rsm_analysis_response = rsm_analysis_response_info.value
    rsm_analysis_payload = rsm_analysis_response.json()
    rsm_design_id = rsm_analysis_payload["design_id"]
    rsm_analysis_id = rsm_analysis_payload["analysis_id"]

    expect(
        page.get_by_role("heading", name="Quadratic response surface")
    ).to_be_visible(timeout=20_000)
    expect(
        page.get_by_role("img", name="Temperature와 Pressure의 예측 반응 contour")
    ).to_be_visible()
    expect(page.get_by_role("columnheader", name="계수")).to_be_visible()
    expect(page.get_by_label("반응표면 적합 요약")).to_contain_text("R²")
    expect(page.get_by_label("반응표면 진단 요약")).to_be_visible()
    expect(page.get_by_label("Run 1 반응")).to_be_disabled()
    expect(page.get_by_label("반응 이름")).to_be_disabled()
    expect(page.get_by_label("반응 단위")).to_be_disabled()
    expect(page.get_by_role("button", name="반응 저장")).to_be_disabled()
    expect(
        page.get_by_text("현재 revision은 읽기 전용입니다", exact=False)
    ).to_be_visible()

    optimizer_button = page.get_by_role("button", name="Response Optimizer 실행")
    expect(optimizer_button).to_be_enabled()
    optimizer_button.click()
    expect(page.get_by_role("heading", name="권장 운전 조건")).to_be_visible(
        timeout=20_000
    )
    optimizer_summary = page.get_by_label("Response Optimizer 결과 요약")
    expect(optimizer_summary).to_contain_text("Composite desirability")
    expect(optimizer_summary).to_contain_text("search_completed")
    expect(optimizer_summary).to_contain_text("전역 최적 보장")
    expect(page.get_by_role("columnheader", name="권장 실제값")).to_be_visible()
    expect(page.get_by_role("columnheader", name="개별 desirability")).to_be_visible()
    expect(
        page.get_by_text("response_optimizer_confirmation_run_required", exact=True)
    ).to_be_visible()

    frontend_base_url = page.url.split("/analysis", 1)[0]
    dedicated_page = page.context.new_page()
    try:
        dedicated_page.goto(
            f"{frontend_base_url}/analysis/regression/regression.response_optimizer",
            wait_until="networkidle",
        )
        expect(dedicated_page).to_have_url(
            re.compile(r"/analysis/doe/doe\.response_optimizer")
        )
        expect(dedicated_page.locator("#workbench-title")).to_have_text(
            "반응 최적화", timeout=20_000
        )
        expect(
            dedicated_page.locator(".workbench-heading .availability-badge")
        ).to_have_text("사용 가능 · 전용 워크플로")
        source_selector = dedicated_page.get_by_label("Source 반응표면 분석")
        source_value = f"{rsm_design_id}:{rsm_analysis_id}"
        expect(
            source_selector.locator(f'option[value="{source_value}"]')
        ).to_have_count(
            1,
            timeout=20_000,
        )
        source_selector.select_option(source_value)
        expect(dedicated_page.locator(".doe-form-section")).to_have_count(0)
        optimizer_root = dedicated_page.locator(
            'section.analysis-result-section[aria-labelledby="response-optimizer-title"]'
        )
        assert_doe_table_visual_consistency(
            optimizer_root, diagnostics, "response-optimizer"
        )
        diagnostics.capture_page(dedicated_page, "doe-optimizer-table-ui.png")
        expect(dedicated_page.get_by_label("선택한 RSM source metadata")).to_be_visible(
            timeout=20_000
        )
        dedicated_optimizer_button = dedicated_page.get_by_role(
            "button", name="Response Optimizer 실행"
        )
        expect(dedicated_optimizer_button).to_be_enabled(timeout=20_000)
        with dedicated_page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith(f"/{rsm_design_id}/optimizations")
        ) as dedicated_optimization_response_info:
            dedicated_optimizer_button.click()
        dedicated_optimization_id = dedicated_optimization_response_info.value.json()[
            "optimization_id"
        ]
        expect(
            dedicated_page.get_by_role("heading", name="권장 운전 조건")
        ).to_be_visible(timeout=20_000)
        expect(dedicated_page).to_have_url(re.compile(f"design_id={rsm_design_id}"))
        expect(dedicated_page).to_have_url(re.compile(f"analysis_id={rsm_analysis_id}"))
        expect(dedicated_page).to_have_url(
            re.compile(f"optimization_id={dedicated_optimization_id}")
        )
        expect(dedicated_page.get_by_role("heading", name="분석 이력")).to_have_count(0)
        expect(
            dedicated_page.get_by_role("heading", name="결과 내보내기")
        ).to_have_count(0)
        dedicated_page.reload(wait_until="networkidle")
        expect(dedicated_page.get_by_label("Source 반응표면 분석")).to_have_value(
            source_value,
            timeout=20_000,
        )
        expect(
            dedicated_page.get_by_role("button", name="Response Optimizer 실행")
        ).to_be_enabled(timeout=20_000)
        expect(
            dedicated_page.get_by_role("heading", name="권장 운전 조건")
        ).to_be_visible(timeout=20_000)
        expect(
            dedicated_page.get_by_label("Response Optimizer 결과 요약")
        ).to_contain_text("Composite desirability")
    finally:
        dedicated_page.close()

    page.get_by_role("button", name="새 revision으로 수정").click()
    expect(page.get_by_label("반응 이름")).to_be_disabled()
    expect(page.get_by_label("Run 1 반응")).to_be_enabled()
    page.get_by_label("Run 1 반응").fill(str(responses[0] + 0.1))
    page.get_by_role("button", name="새 revision 저장").click()
    history = page.get_by_label("RSM response revision history")
    expect(history).to_be_visible(timeout=20_000)
    expect(history).to_contain_text("r2")
    expect(history).to_contain_text("r1")


def verify_dataset_cell_correction(page: Page) -> None:
    selector = page.locator("#active-dataset-version")
    parent_version_id = selector.input_value()

    page.locator(".canonical-preview-section .cell-edit-button").click()
    editor = page.locator(".canonical-preview-section .cell-editor textarea")
    editor.fill("18")
    page.locator(".canonical-preview-section .cell-editor .primary-button").click()
    dialog = page.locator('.confirmation-dialog[role="dialog"]')
    expect(dialog).to_be_visible()
    dialog.locator(".primary-button").click()

    expect(page.locator("#version-title")).to_contain_text("v2", timeout=20_000)
    child_version_id = selector.input_value()
    if child_version_id == parent_version_id:
        raise AssertionError("cell correction did not activate a child dataset version")

    page.locator(".canonical-preview-grid tbody tr").first.locator("td").nth(1).click()
    expect(page.locator(".cell-inspector-value")).to_contain_text("18")

    selector.select_option(parent_version_id)
    expect(page.locator("#version-title")).to_contain_text("v1", timeout=20_000)
    page.locator(".canonical-preview-grid tbody tr").first.locator("td").nth(1).click()
    expect(page.locator(".cell-inspector-value")).to_contain_text("10")

    selector.select_option(child_version_id)
    expect(page.locator("#version-title")).to_contain_text("v2", timeout=20_000)


def verify_latin_hypercube_design(page: Page, diagnostics: E2EDiagnostics) -> None:
    origin = page.evaluate("window.location.origin")
    active_version_id = page.locator("#active-dataset-version").input_value()
    page.goto(
        f"{origin}/analysis/doe/doe.latin_hypercube"
        f"?dataset_version_id={active_version_id}",
        wait_until="networkidle",
    )
    workspace = page.locator(".lhs-workspace")
    expect(workspace).to_be_visible(timeout=20_000)

    expect(workspace.locator(".doe-form-section")).to_have_count(0)
    assert_doe_table_visual_consistency(workspace, diagnostics, "latin-hypercube")
    diagnostics.capture_page(page, "lhs-settings-aligned.png")
    diagnostics.capture_page(page, "doe-lhs-table-ui.png")
    page.get_by_label("factor_1 하한").fill("1")
    page.get_by_label("factor_1 상한").fill("10")
    page.get_by_label("factor_1 설정 방식").select_option("discrete_numeric")
    page.get_by_label("factor_1 실행 간격").fill("1")
    page.get_by_label("factor_1 표시 자리수").fill("0")
    diagnostics.capture_page(page, "doe-discrete-step-factor.png")
    page.get_by_label("실험 수", exact=True).fill("6")
    workspace.locator(":scope > .doe-action-bar .primary-button").click()
    expect(workspace.locator("#lhs-quality-title")).to_be_visible(timeout=20_000)
    expect(workspace.locator(".lhs-run-table tbody tr")).to_have_count(6)
    expect(workspace.locator('a[download][href$="/export.csv"]')).to_be_visible()
    parallel = workspace.get_by_role("img", name="LHS 평행좌표 그림")
    expect(parallel).to_be_visible()
    expect(parallel.locator(".lhs-parallel-run")).to_have_count(6)
    scatter = workspace.get_by_role("img", name="LHS 2요인 투영")
    expect(scatter).to_be_visible()
    expect(scatter.locator(".chart-point")).to_have_count(6)
    workspace.locator(".lhs-parallel-chart").focus()
    page.keyboard.press("ArrowRight")
    expect(
        workspace.locator('.lhs-run-table tbody tr[data-selected="true"]')
    ).to_have_count(1)
    expect(
        workspace.locator('.lhs-run-table tbody tr[data-selected="true"]')
    ).to_contain_text("1")
    scatter.locator(".chart-point").nth(2).focus()
    expect(
        workspace.locator('.lhs-run-table tbody tr[data-selected="true"]')
    ).to_contain_text("3")
    diagnostics.capture_page(page, "lhs-parallel-coordinates.png")
    diagnostics.capture_page(page, "lhs-two-factor-scatter.png")

    response_inputs = workspace.locator(".lhs-response-grid input")
    expect(response_inputs).to_have_count(6)
    for index in range(6):
        response_inputs.nth(index).fill(str(index + 1))
    response_section = workspace.locator(
        'section[aria-labelledby="lhs-response-title"]'
    )
    response_section.locator(".primary-button").click()
    expect(response_section.locator(".status-pill")).to_contain_text(
        "revision 1",
        timeout=20_000,
    )


def verify_bayesian_optimization(page: Page, diagnostics: E2EDiagnostics) -> None:
    select_method_card(page, "실험 계획법", "베이지안 최적화")
    expect(page.locator("#workbench-title")).to_have_text(
        "베이지안 최적화", timeout=15_000
    )
    expect(
        page.get_by_text("앱은 목적함수를 실행하지 않습니다", exact=False)
    ).to_be_visible()

    page.get_by_label("초기 설계 방식").select_option(
        "sha256_counter_uniform_feasible_v1"
    )
    page.get_by_role("button", name="제약 추가").click()
    page.get_by_label("제약 1 x 계수").fill("1")
    page.get_by_label("제약 1 우변").fill("0.75")
    expect(page.locator(".doe-form-section")).to_have_count(0)
    bayesian_root = page.locator(
        '.analysis-run-panel[aria-label="Bayesian 최적화 Study 작업"]'
    )
    assert_doe_table_visual_consistency(bayesian_root, diagnostics, "bayesian")
    diagnostics.capture_page(page, "bayesian-study-builder-aligned.png")
    diagnostics.capture_page(page, "doe-bayesian-table-ui.png")
    page.get_by_label("최적화 목표").select_option("match_target")
    page.get_by_label("목표값", exact=True).fill("0.5")
    page.get_by_label("허용 오차 (선택)").fill("0.1")
    diagnostics.capture_page(page, "bayesian-target-goal.png")
    page.set_viewport_size({"width": 390, "height": 844})
    mobile_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth - window.innerWidth"
    )
    if mobile_overflow > 1:
        raise AssertionError(
            f"Bayesian mobile page overflowed horizontally by {mobile_overflow}px"
        )
    diagnostics.capture_page(page, "bayesian-mobile.png")
    diagnostics.capture_page(page, "doe-table-ui-mobile.png")
    page.set_viewport_size({"width": 1440, "height": 900})
    page.get_by_label("최적화 목표").select_option("maximize")
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and response.url.endswith("/api/v1/bayesian-studies")
    ) as study_response_info:
        page.get_by_role("button", name="스터디 생성").click()
    created_study = study_response_info.value.json()
    initial_history_revision = created_study["observation_history"][
        "history_revision_id"
    ]
    summary = page.get_by_label("Bayesian study 상태")
    expect(summary).to_be_visible(timeout=20_000)
    expect(summary).to_contain_text("0 / 2")
    expect(page.get_by_role("heading", name="요인 정의")).to_be_visible()
    expect(page.get_by_role("heading", name="초기 실험 설계")).to_be_visible()
    factor_definition = page.locator(".bayesian-factor-definition-table")
    expect(factor_definition).to_contain_text("하한")
    expect(factor_definition).to_contain_text("상한")
    expect(factor_definition).to_contain_text("단위")
    initial_design_csv = page.get_by_role("link", name="CSV 다운로드")
    expect(initial_design_csv).to_have_attribute(
        "href", re.compile(r"/bayesian-studies/[0-9a-f-]+/initial-design\.csv$")
    )
    with page.expect_download(timeout=10_000) as initial_download_info:
        initial_design_csv.click()
    if not initial_download_info.value.suggested_filename.endswith(".csv"):
        raise AssertionError("Bayesian initial-design export was not a CSV")
    diagnostics.capture_page(page, "bayesian-study-definition.png")
    stored_constraints = page.get_by_label("Bayesian stored constraints")
    expect(stored_constraints).to_contain_text("constraint_1")
    expect(stored_constraints).to_contain_text("0.750000")
    page.get_by_label("전체 trial 예산").fill("5")

    exploration = page.locator(".bayesian-exploration-section")
    exploration_options = exploration.locator(".bayesian-exploration-options > label")
    expect(exploration_options).to_have_count(4)
    assert_children_do_not_overlap(
        exploration.locator(".bayesian-exploration-options"),
        exploration_options,
        "Bayesian exploration options desktop",
    )
    diagnostics.capture_page(page, "bayesian-goal-layout-desktop.png")
    page.set_viewport_size({"width": 390, "height": 844})
    assert_children_do_not_overlap(
        exploration.locator(".bayesian-exploration-options"),
        exploration_options,
        "Bayesian exploration options mobile",
    )
    bayesian_mobile_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth - window.innerWidth"
    )
    if bayesian_mobile_overflow > 1:
        raise AssertionError(
            f"Bayesian study overflowed mobile viewport by {bayesian_mobile_overflow}px"
        )
    diagnostics.capture_page(page, "bayesian-goal-layout-mobile.png")
    page.set_viewport_size({"width": 1440, "height": 900})

    page.get_by_role("button", name="관측값 붙여넣기").click()
    page.get_by_label("Bayesian 관측값 붙여넣기").fill("0.8\n1.0")
    diagnostics.capture_page(page, "bayesian-observation-paste.png")
    page.get_by_role("button", name="앞 pending trial에 적용").click()
    expect(page.get_by_label("Trial 1 관측값")).to_have_value("0.8")
    expect(page.get_by_label("Trial 2 관측값")).to_have_value("1.0")
    page.get_by_role("button", name="입력한 관측 2건 저장").click()
    confirmation = page.get_by_role("alertdialog")
    expect(confirmation).to_contain_text("관측값 2건 저장")
    diagnostics.capture_page(page, "bayesian-bulk-observations.png")
    with page.expect_response(
        lambda response: response.request.method == "PUT"
        and response.url.endswith("/observations/batch")
    ) as observation_batch_info:
        confirmation.get_by_role("button", name="2건 저장").click()
    batch_payload = observation_batch_info.value.json()
    if batch_payload["completed_trial_count"] != 2:
        raise AssertionError("Bayesian observation batch did not complete two trials")
    if (
        batch_payload["observation_history"]["history_revision_id"]
        == initial_history_revision
    ):
        raise AssertionError("Bayesian observation batch did not create one revision")
    expect(page.get_by_label("Trial 1 관측값")).to_have_count(0, timeout=20_000)
    expect(page.get_by_label("Trial 2 관측값")).to_have_count(0)
    recommendation_button = page.get_by_role("button", name="추천 batch 생성")
    expect(recommendation_button).to_be_enabled(timeout=20_000)
    page.get_by_role("radio", name="여러 실험을 동시에 수행").check()
    page.get_by_label("한 번에 추천할 실험 수").fill("2")
    diagnostics.capture_page(page, "bayesian-parallel-batch-settings.png")
    page.get_by_role("radio", name="결과를 하나씩 반영").check()
    diagnostics.capture_page(page, "bayesian-sequential-settings.png")
    recommendation_button.click()

    expect(page.get_by_role("heading", name="추천 batch 결과")).to_be_visible(
        timeout=45_000
    )
    expect(page).to_have_url(re.compile(r"study_id=[0-9a-f-]+"))
    expect(page).to_have_url(re.compile(r"batch_id=[0-9a-f-]+"))
    result_section = page.locator(
        'section[aria-labelledby="bayesian-batch-result-title"]'
    )
    diagnostics.capture_page(page, "bayesian-batch-result.png")
    expect(result_section.get_by_text("실험 대기", exact=True)).to_be_visible()
    expect(page.get_by_text("추천", exact=True)).to_be_visible()
    result_section.get_by_text("왜 이 조건?", exact=True).click()
    expect(result_section).to_contain_text("constraint_1")
    expect(result_section).to_contain_text("충족")
    expect(
        result_section.get_by_text("전역 최적을 보장하지 않습니다", exact=False)
    ).to_be_visible()

    page.get_by_label("Trial 3 관측값").fill("0.97")
    page.get_by_role("button", name="입력한 관측 1건 저장").click()
    page.get_by_role("alertdialog").get_by_role("button", name="1건 저장").click()
    expect(result_section.get_by_text("전체 완료", exact=True)).to_be_visible(
        timeout=20_000
    )

    expect(recommendation_button).to_be_enabled(timeout=20_000)
    recommendation_button.click()
    trial_four_input = page.get_by_label("Trial 4 관측값")
    expect(trial_four_input).to_be_visible(timeout=45_000)
    trial_four_row = trial_four_input.locator("xpath=ancestor::tr")
    abandoned_coordinates = trial_four_row.locator("td").nth(2).inner_text()
    trial_four_row.get_by_role("button", name="실험 포기", exact=True).click()
    abandon_confirmation = page.get_by_label("Trial 4 terminal action 확인")
    expect(abandon_confirmation).to_contain_text("향후 추천에서 제외")
    abandon_confirmation.get_by_role("button", name="Abandon 확인").click()
    expect(result_section.get_by_text("전체 포기", exact=True)).to_be_visible(
        timeout=20_000
    )

    expect(recommendation_button).to_be_enabled(timeout=20_000)
    recommendation_button.click()
    trial_five_input = page.get_by_label("Trial 5 관측값")
    expect(trial_five_input).to_be_visible(timeout=45_000)
    trial_five_row = trial_five_input.locator("xpath=ancestor::tr")
    next_coordinates = trial_five_row.locator("td").nth(2).inner_text()
    assert next_coordinates != abandoned_coordinates
    expect(result_section.get_by_text("실험 대기", exact=True)).to_be_visible()
    expect(recommendation_button).to_be_disabled()
    expect(
        page.get_by_text("남은 trial 예산보다 batch 수가 큽니다", exact=False)
    ).to_be_visible()

    study_selector = page.get_by_label("저장된 Bayesian study")
    study_id = study_selector.input_value()
    page.reload(wait_until="networkidle")
    expect(page.locator("#workbench-title")).to_have_text(
        "베이지안 최적화", timeout=20_000
    )
    restored_selector = page.get_by_label("저장된 Bayesian study")
    expect(restored_selector).to_have_value(study_id, timeout=20_000)
    expect(page.get_by_label("Trial 5 관측값")).to_be_visible(timeout=20_000)
    expect(
        page.get_by_text("남은 trial 예산보다 batch 수가 큽니다", exact=False)
    ).to_be_visible()
    expect(
        page.locator(
            'section[aria-labelledby="bayesian-batch-result-title"]'
        ).get_by_text("실험 대기", exact=True)
    ).to_be_visible()

    page.get_by_label("Trial 5 관측값").fill("0.96")
    page.get_by_role("button", name="입력한 관측 1건 저장").click()
    page.get_by_role("alertdialog").get_by_role("button", name="1건 저장").click()
    expect(page.get_by_label("Trial 5 관측값")).to_have_count(0, timeout=20_000)

    page.get_by_label("Bayesian study 종료 메모").fill("E2E confirmation complete")
    complete_study = page.get_by_role("button", name="Study 완료")
    expect(complete_study).to_be_enabled(timeout=20_000)
    complete_study.click()
    close_confirmation = page.get_by_label("Bayesian study terminal action 확인")
    expect(close_confirmation).to_contain_text("다시 열 수 없습니다")
    expect(close_confirmation).to_contain_text("전역 최적해 달성")
    close_confirmation.get_by_role("button", name="종료 확인").click()
    lifecycle = page.get_by_label("Bayesian study 종료 기록")
    expect(lifecycle).to_be_visible(timeout=20_000)
    expect(lifecycle).to_contain_text("completed")
    expect(lifecycle).to_contain_text("confirmation_complete")
    expect(page.get_by_label("전체 trial 예산")).to_be_disabled()
    expect(page.get_by_role("button", name="추천 batch 생성")).to_be_disabled()

    page.reload(wait_until="networkidle")
    restored_selector = page.get_by_label("저장된 Bayesian study")
    expect(restored_selector).to_have_value(study_id, timeout=20_000)
    expect(page.get_by_label("Bayesian study 종료 기록")).to_be_visible(timeout=20_000)
    expect(
        page.get_by_role("button", name="이 정의로 successor study 준비")
    ).to_be_visible()
    page.get_by_role("button", name="이 정의로 successor study 준비").click()
    expect(
        page.get_by_text(
            "동일한 seed를 사용하면 동일한 초기 조건이 다시 생성될 수 있습니다"
        )
    ).to_be_visible()
    expect(page.get_by_role("button", name="새 random seed 생성")).to_be_visible()
    page.get_by_role("button", name="후속 스터디 생성 취소").click()
    page.get_by_label("Bayesian 최적화").get_by_role(
        "button", name="삭제 영향 확인"
    ).click()
    deletion_impact = page.get_by_label("Bayesian study 삭제 영향")
    expect(deletion_impact).to_be_visible(timeout=20_000)
    expect(deletion_impact).to_contain_text("파일 0개")
    expect(deletion_impact).to_contain_text("batch 3건 / item 3건")
    deletion_impact.get_by_role("button", name="불가역 삭제 확인").click()
    deletion_confirmation = page.get_by_label(
        "Bayesian study irreversible deletion 확인"
    )
    expect(deletion_confirmation).to_contain_text("복원할 수 없으며")
    expect(deletion_confirmation).to_contain_text("cascade 또는 successor 삭제")
    deletion_confirmation.get_by_role("button", name="영구 삭제 확인").click()
    expect(restored_selector.locator(f'option[value="{study_id}"]')).to_have_count(
        0, timeout=20_000
    )


def verify_xlsx_file_upload(page: Page, temp_dir: Path) -> None:
    try:
        xlsx_path = temp_dir / "browser-upload-sample.xlsx"
        xlsx_path.write_bytes(minimal_xlsx_workbook_bytes())

        open_primary_navigation(page, "데이터셋")
        page.get_by_label("원본 데이터 파일").set_input_files(str(xlsx_path))
        page.get_by_role("button", name="업로드").click()
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(
            timeout=15_000
        )
        expect(page.get_by_text("browser-upload-sample.xlsx")).to_be_visible()

        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
        expect(page.locator("#version-title")).to_contain_text("v1", timeout=20_000)
        expect_dataset_context_counts(page, row_label="2행", column_label="3컬럼")
        expect(page.get_by_role("columnheader", name="alpha")).to_be_visible()
        expect(page.get_by_role("columnheader", name="flag")).to_be_visible()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def verify_csv_file_upload_and_error_recovery(page: Page, temp_dir: Path) -> None:
    try:
        empty_csv_path = temp_dir / "empty-upload.csv"
        empty_csv_path.write_text("", encoding="utf-8")
        csv_path = temp_dir / "브라우저-csv-upload.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "Batch,Measurement",
                    "A,1.5",
                    "B,2.5",
                    "C,3.5",
                ],
            ),
            encoding="utf-8",
        )

        open_primary_navigation(page, "데이터셋")
        page.get_by_label("원본 데이터 파일").set_input_files(str(empty_csv_path))
        page.get_by_role("button", name="업로드").click()
        expect(page.get_by_role("alert")).to_contain_text("empty_file", timeout=15_000)

        page.get_by_label("원본 데이터 파일").set_input_files(str(csv_path))
        expect(page.get_by_role("alert")).not_to_be_visible()
        page.get_by_role("button", name="업로드").click()
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(
            timeout=15_000
        )
        expect(page.get_by_text("브라우저-csv-upload.csv")).to_be_visible()

        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
        expect(page.locator("#version-title")).to_contain_text("v1", timeout=20_000)
        expect_dataset_context_counts(page, row_label="3행", column_label="2컬럼")
        expect(page.get_by_role("columnheader", name="Batch")).to_be_visible()
        expect(page.get_by_role("columnheader", name="Measurement")).to_be_visible()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def verify_parser_option_editing(page: Page, temp_dir: Path) -> None:
    try:
        csv_path = temp_dir / "parser-options-edit.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "Generated,Do not use",
                    "Alpha,Beta",
                    "one,100",
                    "two,MISSING",
                ],
            ),
            encoding="utf-8",
        )

        open_primary_navigation(page, "데이터셋")
        page.get_by_label("원본 데이터 파일").set_input_files(str(csv_path))
        page.get_by_role("button", name="업로드").click()
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(
            timeout=15_000
        )
        expect(page.get_by_text("parser-options-edit.csv")).to_be_visible()

        page.get_by_label("첫 데이터 행을 헤더로 사용").check()
        page.get_by_label("헤더 행").fill("2")
        page.get_by_label("결측 토큰").fill(",NA,N/A,null,N/T,MISSING")

        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
        expect(page.locator("#version-title")).to_contain_text("v1", timeout=20_000)
        expect_dataset_context_counts(page, row_label="2행", column_label="2컬럼")
        expect(page.get_by_role("columnheader", name="Alpha")).to_be_visible()
        expect(page.get_by_role("columnheader", name="Beta")).to_be_visible()
        expect(
            page.locator(".canonical-preview-grid .missing-cell").filter(
                has_text="결측"
            )
        ).to_be_visible()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def verify_delimiter_option_editing(page: Page, temp_dir: Path) -> None:
    try:
        csv_path = temp_dir / "semicolon-delimiter.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "Category;Value",
                    "Left;10",
                    "Right;20",
                ],
            ),
            encoding="utf-8",
        )

        open_primary_navigation(page, "데이터셋")
        page.get_by_label("원본 데이터 파일").set_input_files(str(csv_path))
        page.get_by_role("button", name="업로드").click()
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(
            timeout=15_000
        )
        expect(page.get_by_text("semicolon-delimiter.csv")).to_be_visible()

        page.get_by_label("구분자").select_option(";")

        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
        expect(page.locator("#version-title")).to_contain_text("v1", timeout=20_000)
        expect_dataset_context_counts(page, row_label="2행", column_label="2컬럼")
        expect(page.get_by_role("columnheader", name="Category")).to_be_visible()
        expect(page.get_by_role("columnheader", name="Value")).to_be_visible()
        expect(page.get_by_role("gridcell", name="Left", exact=True)).to_be_visible()
        expect(page.get_by_role("gridcell", name="20", exact=True)).to_be_visible()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def verify_xlsx_sheet_selection(page: Page, temp_dir: Path) -> None:
    try:
        xlsx_path = temp_dir / "multi-sheet-upload.xlsx"
        xlsx_path.write_bytes(multi_sheet_xlsx_workbook_bytes())

        open_primary_navigation(page, "데이터셋")
        page.get_by_label("원본 데이터 파일").set_input_files(str(xlsx_path))
        page.get_by_role("button", name="업로드").click()
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(
            timeout=15_000
        )
        expect(page.get_by_text("multi-sheet-upload.xlsx")).to_be_visible()

        page.get_by_label("시트명").fill("Missing")
        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
        expect(page.get_by_role("alert")).to_contain_text(
            "xlsx_sheet_not_found", timeout=15_000
        )
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible()

        page.get_by_label("시트명").fill("Measurements")

        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
        expect(page.locator("#version-title")).to_contain_text("v1", timeout=20_000)
        expect_dataset_context_counts(page, row_label="2행", column_label="2컬럼")
        expect(page.get_by_role("columnheader", name="Station")).to_be_visible()
        expect(page.get_by_role("columnheader", name="Reading")).to_be_visible()
        expect(page.get_by_role("gridcell", name="S2", exact=True)).to_be_visible()
        expect(page.get_by_role("gridcell", name="43", exact=True)).to_be_visible()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def verify_text_encoding_selection(page: Page, temp_dir: Path) -> None:
    try:
        csv_path = temp_dir / "cp949-upload.csv"
        csv_path.write_bytes(
            (("A" * 8300) + "\n" + "이름,값\n" + "홍길동,1\n" + "김철수,2\n").encode(
                "cp949"
            ),
        )

        open_primary_navigation(page, "데이터셋")
        page.get_by_label("원본 데이터 파일").set_input_files(str(csv_path))
        page.get_by_role("button", name="업로드").click()
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(
            timeout=15_000
        )
        expect(page.get_by_text("cp949-upload.csv")).to_be_visible()

        page.get_by_label("구분자").select_option(",")
        page.get_by_label("첫 데이터 행을 헤더로 사용").check()
        page.get_by_label("헤더 행").fill("2")
        page.get_by_label("인코딩").select_option("utf-8")
        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
        expect(page.get_by_role("alert")).to_contain_text(
            "text_decoding_failed", timeout=15_000
        )
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible()

        page.get_by_label("인코딩").select_option("cp949")

        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
        expect(page.locator("#version-title")).to_contain_text("v1", timeout=20_000)
        expect_dataset_context_counts(page, row_label="2행", column_label="2컬럼")
        expect(
            page.get_by_role("columnheader", name="이름", exact=True)
        ).to_be_visible()
        expect(page.get_by_role("columnheader", name="값", exact=True)).to_be_visible()
        expect(page.get_by_role("gridcell", name="홍길동", exact=True)).to_be_visible()
        expect(page.get_by_role("gridcell", name="김철수", exact=True)).to_be_visible()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def paste_plain_text(page: Page, text: str) -> None:
    surface = page.get_by_role("textbox", name="복사한 표 붙여넣기")
    surface.focus()
    surface.evaluate(
        """
        (element, value) => {
          const clipboard = new DataTransfer();
          clipboard.setData("text/plain", value);
          clipboard.setData("text/html", "<table><tr><td>must-not-render</td></tr></table>");
          element.dispatchEvent(new ClipboardEvent("paste", {
            bubbles: true,
            cancelable: true,
            clipboardData: clipboard,
          }));
        }
        """,
        text,
    )


def expect_dataset_context_counts(
    page: Page, *, row_label: str, column_label: str
) -> None:
    context_bar = page.locator('[aria-label="데이터셋 컨텍스트"]')
    row_value = row_label.removesuffix("행")
    column_value = column_label.removesuffix("컬럼").removesuffix("열")
    row_stat = context_bar.locator(
        ".active-dataset-stat", has_text=re.compile(rf"^행\s*{row_value}$")
    )
    column_stat = context_bar.locator(
        ".active-dataset-stat", has_text=re.compile(rf"^열\s*{column_value}$")
    )
    expect(row_stat).to_be_visible()
    expect(column_stat).to_be_visible()


def minimal_xlsx_workbook_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            "\n".join(
                [
                    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
                    '<Default Extension="rels" '
                    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
                    '<Default Extension="xml" ContentType="application/xml"/>',
                    '<Override PartName="/xl/workbook.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.'
                    'spreadsheetml.sheet.main+xml"/>',
                    '<Override PartName="/xl/worksheets/sheet1.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.'
                    'spreadsheetml.worksheet+xml"/>',
                    "</Types>",
                ],
            ),
        )
        archive.writestr(
            "xl/workbook.xml",
            """
            <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
              xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <sheets>
                <sheet name="Sheet1" sheetId="1" r:id="rId1"/>
              </sheets>
            </workbook>
            """,
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """
            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rId1"
                Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
                Target="worksheets/sheet1.xml"/>
            </Relationships>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <sheetData>
                <row r="1">
                  <c r="A1" t="inlineStr"><is><t>alpha</t></is></c>
                  <c r="B1" t="inlineStr"><is><t>beta</t></is></c>
                  <c r="C1" t="inlineStr"><is><t>flag</t></is></c>
                </row>
                <row r="2">
                  <c r="A2"><v>1</v></c>
                  <c r="B2" t="inlineStr"><is><t>x</t></is></c>
                  <c r="C2" t="b"><v>1</v></c>
                </row>
                <row r="3">
                  <c r="A3"><v>2</v></c>
                  <c r="B3" t="inlineStr"><is><t>N/T</t></is></c>
                  <c r="C3" t="b"><v>0</v></c>
                </row>
              </sheetData>
            </worksheet>
            """,
        )
    return buffer.getvalue()


def multi_sheet_xlsx_workbook_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            "\n".join(
                [
                    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
                    '<Default Extension="rels" '
                    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
                    '<Default Extension="xml" ContentType="application/xml"/>',
                    '<Override PartName="/xl/workbook.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.'
                    'spreadsheetml.sheet.main+xml"/>',
                    '<Override PartName="/xl/worksheets/sheet1.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.'
                    'spreadsheetml.worksheet+xml"/>',
                    '<Override PartName="/xl/worksheets/sheet2.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.'
                    'spreadsheetml.worksheet+xml"/>',
                    "</Types>",
                ],
            ),
        )
        archive.writestr(
            "xl/workbook.xml",
            """
            <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
              xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <sheets>
                <sheet name="Summary" sheetId="1" r:id="rId1"/>
                <sheet name="Measurements" sheetId="2" r:id="rId2"/>
              </sheets>
            </workbook>
            """,
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """
            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rId1"
                Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
                Target="worksheets/sheet1.xml"/>
              <Relationship Id="rId2"
                Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
                Target="worksheets/sheet2.xml"/>
            </Relationships>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <sheetData>
                <row r="1">
                  <c r="A1" t="inlineStr"><is><t>Ignored</t></is></c>
                  <c r="B1" t="inlineStr"><is><t>Value</t></is></c>
                </row>
                <row r="2">
                  <c r="A2" t="inlineStr"><is><t>summary</t></is></c>
                  <c r="B2"><v>999</v></c>
                </row>
              </sheetData>
            </worksheet>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet2.xml",
            """
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <sheetData>
                <row r="1">
                  <c r="A1" t="inlineStr"><is><t>Station</t></is></c>
                  <c r="B1" t="inlineStr"><is><t>Reading</t></is></c>
                </row>
                <row r="2">
                  <c r="A2" t="inlineStr"><is><t>S1</t></is></c>
                  <c r="B2"><v>42</v></c>
                </row>
                <row r="3">
                  <c r="A3" t="inlineStr"><is><t>S2</t></is></c>
                  <c r="B3"><v>43</v></c>
                </row>
              </sheetData>
            </worksheet>
            """,
        )
    return buffer.getvalue()


def terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def print_log_tail(log_path: Path, label: str, max_bytes: int = 8000) -> None:
    print(f"\n--- {label} log tail ({log_path.name}) ---", file=sys.stderr)
    try:
        data = log_path.read_bytes()
    except OSError as exc:
        print(f"could not read log: {exc}", file=sys.stderr)
        return
    tail = data[-max_bytes:]
    print(tail.decode("utf-8", errors="replace"), file=sys.stderr)


def print_recent_logs(log_root: Path, max_bytes: int = 8000) -> None:
    for log_path in sorted(log_root.glob("*.log")):
        print_log_tail(log_path, log_path.stem, max_bytes=max_bytes)


if __name__ == "__main__":
    raise SystemExit(main())
