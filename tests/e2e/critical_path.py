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
    BrowserContext,
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

REGRESSION_SAMPLE_DATA = """y\tx\tgroup
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

REGRESSION_TARGET_DATA = """y\tx\tgroup
0\t1\tA
0\t3.5\tB
0\t5.5\tC
0\t6\tA
"""

ATTRIBUTE_CONTROL_CHART_DATA = """defectives\tsample_size
12\t50
15\t50
8\t50
10\t50
4\t50
7\t50
16\t50
9\t50
14\t50
10\t50
5\t50
6\t50
17\t50
12\t50
22\t50
8\t50
10\t50
5\t50
13\t50
11\t50
20\t50
18\t50
24\t50
15\t50
9\t50
12\t50
7\t50
13\t50
9\t50
6\t50
"""

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


def run_browser_flow(frontend_base_url: str, diagnostics: E2EDiagnostics) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page: Page | None = None
        try:
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            diagnostics.step("open Workbench")
            page.goto(frontend_base_url, wait_until="networkidle")

            expect(page.get_by_text("DataLab Studio")).to_be_visible()
            expect(page.get_by_text("API ready")).to_be_visible(timeout=15_000)
            diagnostics.step("paste synthetic TSV and confirm schema")

            page.get_by_label("복사한 표 붙여넣기").fill(SAMPLE_DATA)
            page.get_by_role("button", name="붙여넣기 데이터 등록").click()
            expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(
                timeout=15_000
            )

            page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
            expect(
                page.get_by_role("heading", name=re.compile(r"Dataset version v1")),
            ).to_be_visible(timeout=20_000)
            expect_dataset_context_counts(page, row_label="6행", column_label="2컬럼")

            page.get_by_role("button", name="분석", exact=True).click()
            expect(page.get_by_role("heading", name="기술통계 실행")).to_be_visible()
            page.get_by_role("button", name="기술통계 실행").click()
            diagnostics.step("run descriptive statistics")
            expect(
                page.locator(".result-table").filter(has_text="Value")
            ).to_be_visible(
                timeout=20_000,
            )

            page.get_by_role(
                "button", name=re.compile(r"2-표본 t-검정 메서드 보기")
            ).click()
            expect(
                page.get_by_role("heading", name="2-표본 t-검정 실행")
            ).to_be_visible()
            page.get_by_role("button", name="2-표본 t-검정 실행").click()
            diagnostics.step("run two-sample t test")
            expect(
                page.locator(".result-table").filter(has_text="Hedges g")
            ).to_be_visible(
                timeout=20_000,
            )

            diagnostics.step("create, download, and delete one export")
            create_exports(page)
            diagnostics.step("restore and compare saved results")
            restore_and_compare_saved_results(page)
            diagnostics.step("delete one stored analysis run")
            delete_one_saved_analysis_run(page)
            diagnostics.step("verify schema stale behavior")
            verify_schema_stale_behavior(page)
            diagnostics.step("verify linear model fit and prediction")
            verify_linear_model_fit_and_prediction(page)
            diagnostics.step("verify attribute control chart")
            verify_attribute_control_chart(page)
            diagnostics.step("verify DOE factorial analysis")
            verify_doe_factorial_analysis(page)
            diagnostics.step("verify DOE response surface analysis and optimization")
            verify_doe_response_surface_analysis(page)
            diagnostics.step("verify Bayesian study observations and recommendation")
            verify_bayesian_optimization(page)
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


def create_exports(page: Page) -> None:
    page.get_by_role("button", name="JSON 생성").click()
    expect(page.get_by_role("button", name="JSON 다운로드")).to_be_visible(
        timeout=15_000
    )

    page.get_by_role("button", name="CSV 생성").click()
    expect(page.get_by_role("button", name="CSV 다운로드")).to_be_visible(
        timeout=15_000
    )

    page.get_by_role("button", name="HTML 생성").click()
    expect(page.get_by_role("button", name="HTML 다운로드")).to_be_visible(
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
    expect(export_items).to_have_count(3, timeout=15_000)
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
    expect(export_items).to_have_count(2, timeout=15_000)
    expect(page.locator(".result-table").filter(has_text="Hedges g")).to_be_visible()


def restore_and_compare_saved_results(page: Page) -> None:
    history_items = page.locator(".analysis-history-item")
    expect(history_items).to_have_count(2, timeout=20_000)
    expect(page.get_by_text("현재 데이터셋의 저장된 분석")).to_be_visible()

    history_items.nth(0).get_by_role("button", name="결과 불러오기").click()
    expect(page.get_by_text("불러온 결과")).to_be_visible(timeout=15_000)

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
    history_items.nth(1).get_by_role("button", name="결과 불러오기").click()
    expect(page.get_by_text("불러온 결과")).to_be_visible(timeout=15_000)

    history_items.nth(1).get_by_role("button", name="삭제 영향 확인").click()
    deletion_impact = page.get_by_label("analysis run 삭제 영향")
    expect(deletion_impact).to_contain_text("파일 2개", timeout=15_000)
    expect(deletion_impact).to_contain_text("export 0개")
    deletion_impact.get_by_role("button", name="영구 삭제 확인").click()
    deletion_confirmation = page.get_by_label(
        "analysis run irreversible deletion 확인"
    )
    expect(deletion_confirmation).to_contain_text("복원할 수 없습니다")
    deletion_confirmation.get_by_role(
        "button", name="분석 실행 영구 삭제"
    ).click()

    expect(page.get_by_text(re.compile(r"분석 실행 삭제 완료"))).to_be_visible(
        timeout=15_000
    )
    expect(history_items).to_have_count(1, timeout=15_000)
    expect(page.get_by_text("불러온 결과")).to_have_count(0)
    expect(page.get_by_text("비교 결과")).to_have_count(0)


def verify_schema_stale_behavior(page: Page) -> None:
    page.get_by_role("button", name="데이터셋", exact=True).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Dataset version v1")),
    ).to_be_visible(timeout=15_000)

    page.get_by_role("button", name="스키마 저장").click()
    expect(page.get_by_role("button", name="스키마 저장")).to_be_enabled(timeout=15_000)

    page.get_by_role("button", name="분석", exact=True).click()
    expect(page.get_by_text("현재 데이터셋의 저장된 분석")).to_be_visible(
        timeout=15_000
    )
    page.get_by_role("button", name="새로고침").click()
    expect(page.locator(".analysis-history-item")).to_have_count(1, timeout=15_000)
    expect(page.locator(".analysis-history-panel .stale-badge")).to_have_count(0)

    page.get_by_role("button", name="데이터셋", exact=True).click()
    value_display_input = page.get_by_label("Value 표시명")
    value_display_input.fill("Measurement Value")
    page.get_by_role("button", name="스키마 저장").click()
    expect(value_display_input).to_have_value("Measurement Value", timeout=15_000)

    page.get_by_role("button", name="분석", exact=True).click()
    page.get_by_role("button", name="새로고침").click()
    expect(page.locator(".analysis-history-item")).to_have_count(1, timeout=15_000)
    expect(page.locator(".analysis-history-panel .stale-badge")).to_have_count(1)
    expect(page.get_by_text("stale · 재검토 필요").first).to_be_visible()


def verify_linear_model_fit_and_prediction(page: Page) -> None:
    page.get_by_role("button", name="데이터셋", exact=True).click()
    page.get_by_label("복사한 표 붙여넣기").fill(REGRESSION_TARGET_DATA)
    page.get_by_role("button", name="붙여넣기 데이터 등록").click()
    expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
    page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
    expect_dataset_context_counts(page, row_label="4행", column_label="3컬럼")

    page.get_by_label("복사한 표 붙여넣기").fill(REGRESSION_SAMPLE_DATA)
    page.get_by_role("button", name="붙여넣기 데이터 등록").click()
    expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)

    page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
    expect_dataset_context_counts(page, row_label="12행", column_label="3컬럼")
    page.get_by_role("button", name="분석", exact=True).click()
    page.get_by_role(
        "button",
        name=re.compile(r"상관관계 및 회귀분석"),
    ).click()
    page.get_by_label("분석 메서드").get_by_role(
        "button",
        name=re.compile(r"^회귀모형 적합"),
    ).click()
    expect(page.get_by_role("heading", name="회귀모형 적합 실행")).to_be_visible()
    expect_lazy_analysis_module(page, "RegressionAnalysisPanels")

    page.get_by_label("반응 변수").select_option(label="y")
    predictor_options = page.get_by_label("예측변수")
    x_predictor = predictor_options.get_by_role("checkbox", name=re.compile(r"^x"))
    group_predictor = predictor_options.get_by_role(
        "checkbox",
        name=re.compile(r"^group"),
    )
    x_predictor.check()
    expect(x_predictor).to_be_checked()
    expect(group_predictor).to_be_checked()

    page.get_by_role("button", name="회귀모형 적합 실행").click()
    model_summary = page.get_by_label("회귀모형 요약")
    expect(model_summary).to_be_visible(timeout=20_000)
    expect(model_summary).to_contain_text("12 / 12")
    expect(model_summary).to_contain_text("Model ID")
    expect(model_summary).to_contain_text("Manifest")
    expect(page.get_by_role("heading", name="예측 사전점검")).to_be_visible()

    target_selector = page.get_by_label("예측 대상 데이터셋 버전")
    target_option = target_selector.locator("option").filter(has_text="4행 × 3열")
    expect(target_option).to_have_count(1, timeout=15_000)
    target_version_id = target_option.get_attribute("value")
    if target_version_id is None:
        raise AssertionError(
            "Prediction target option did not expose a dataset version ID"
        )
    target_selector.select_option(target_version_id)
    expect(target_selector).to_have_value(target_version_id)

    page.get_by_role("button", name="사전점검 실행").click()
    preflight_summary = page.get_by_label("예측 사전점검 요약")
    expect(preflight_summary).to_be_visible(timeout=20_000)
    expect(preflight_summary).to_contain_text("예측 준비 가능")
    expect(preflight_summary).to_contain_text("4 / 4")
    expect(preflight_summary).to_contain_text("다름")

    page.get_by_role("button", name="예측 실행").click()
    prediction_summary = page.get_by_label("예측 결과 요약")
    expect(prediction_summary).to_be_visible(timeout=20_000)
    expect(prediction_summary).to_contain_text("4 / 4")
    expect(prediction_summary).to_contain_text("Prediction ID")
    expect(page.get_by_role("heading", name="예측 구간 차트")).to_be_visible()
    expect(page.locator(".prediction-interval-line")).to_have_count(4)
    prediction_table = page.locator(".result-table").filter(
        has_text="Prediction interval"
    )
    expect(prediction_table).to_be_visible()
    expect(prediction_table.get_by_role("columnheader", name="Mean CI")).to_be_visible()
    expect(prediction_table.locator("tbody tr")).to_have_count(4)

    page.get_by_role("button", name="전체 예측 CSV 생성").click()
    csv_download_button = page.get_by_role("button", name="전체 예측 CSV 다운로드")
    expect(csv_download_button).to_be_visible(timeout=15_000)
    expect(page.get_by_label("전체 예측 CSV export")).to_contain_text("4행")
    try:
        with page.expect_download(timeout=10_000) as download_info:
            csv_download_button.click()
        download = download_info.value
        if not download.suggested_filename.endswith(".csv"):
            raise AssertionError(
                f"unexpected prediction CSV download name: {download.suggested_filename}",
            )
    except PlaywrightTimeoutError as exc:
        raise AssertionError("Prediction CSV export download did not start") from exc

    model_retention = page.get_by_role("region", name="저장 모델 관리")
    model_retention.get_by_role("button", name="삭제 영향 확인").click()
    expect(model_retention.get_by_text("예측 참조 1건", exact=True)).to_be_visible(
        timeout=15_000
    )
    expect(
        model_retention.get_by_text(
            "종속 예측 결과를 먼저 삭제해야 모델을 삭제할 수 있습니다."
        )
    ).to_be_visible()
    expect(model_retention.get_by_role("button", name="모델 삭제")).to_be_disabled()


def verify_attribute_control_chart(page: Page) -> None:
    page.get_by_role("button", name="데이터셋", exact=True).click()
    page.get_by_label("복사한 표 붙여넣기").fill(ATTRIBUTE_CONTROL_BASELINE_DATA)
    page.get_by_role("button", name="붙여넣기 데이터 등록").click()
    expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
    page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
    expect_dataset_context_counts(page, row_label="20행", column_label="2컬럼")

    page.get_by_role("button", name="분석", exact=True).click()
    page.get_by_role("button", name="계수형 관리도 메서드 보기").click()
    expect(page.get_by_role("heading", name="계수형 관리도 실행")).to_be_visible()
    expect_lazy_analysis_module(page, "QualityAnalysisPanels")
    expect(page.get_by_text("Phase I은 현재 데이터에서 기준선을 추정합니다", exact=False)).to_be_visible()
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

    page.get_by_role("button", name="데이터셋", exact=True).click()
    page.get_by_label("복사한 표 붙여넣기").fill(ATTRIBUTE_CONTROL_CHART_DATA)
    page.get_by_role("button", name="붙여넣기 데이터 등록").click()
    expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
    page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
    expect_dataset_context_counts(page, row_label="30행", column_label="2컬럼")
    page.get_by_role("button", name="분석", exact=True).click()
    page.get_by_role("button", name="계수형 관리도 메서드 보기").click()
    page.get_by_role("radio", name="Phase II 고정 한계 모니터링").click()
    limit_set_select = page.get_by_label("검증된 limit set")
    expect(limit_set_select).to_be_enabled(timeout=20_000)
    limit_set_select.select_option(index=1)
    expect(page.get_by_text("호환성 확인 중...")).to_have_count(0, timeout=20_000)
    phase_2_button = page.get_by_role("button", name="P 관리도 실행")
    expect(phase_2_button).to_be_enabled(timeout=20_000)
    phase_2_button.click()
    expect(summary).to_be_visible(timeout=20_000)
    expect(summary).to_contain_text("30 / 30")
    expect(summary).to_contain_text("Phase II")
    expect(summary).to_contain_text("검증된 immutable limit set")
    expect(summary).to_contain_text("Limit set")
    expect(page.get_by_role("img", name=re.compile(r"P 관리도.*신호"))).to_be_visible()
    page.get_by_role("button", name="limit set 삭제 영향 확인").click()
    expect(page.get_by_text("Phase II 참조 1건", exact=True)).to_be_visible(timeout=15_000)
    expect(
        page.get_by_text("이 limit set을 참조하는 Phase II 분석을 먼저 삭제해야 합니다.")
    ).to_be_visible()
    expect(
        page.get_by_role("button", name="limit set 삭제", exact=True)
    ).to_be_disabled()


def verify_doe_factorial_analysis(page: Page) -> None:
    page.get_by_role("button", name="분석", exact=True).click()
    page.get_by_role("button", name="실험 계획 생성 메서드 보기").click()
    expect(
        page.get_by_role("heading", name="2-level full factorial 설계 생성")
    ).to_be_visible()
    expect_lazy_analysis_module(page, "DoeAnalysisPanels")

    page.get_by_label("반복", exact=True).fill("2")
    page.get_by_label("센터점", exact=True).fill("1")
    page.get_by_label("랜덤화", exact=True).uncheck()
    page.get_by_role("button", name="DOE 설계 생성").click()
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
    expect(page.locator(".analysis-result-section")).to_contain_text("0.3.0")
    expect(page.get_by_label("DOE 잔차 진단 요약")).to_be_visible()
    expect(page.get_by_label("run 1 response")).to_be_disabled()
    expect(page.get_by_role("button", name="분석 후 반응 잠금")).to_be_disabled()
    expect(page.get_by_text("읽기 전용입니다", exact=False)).to_be_visible()
    page.get_by_role("button", name="새 revision으로 수정").click()
    expect(page.get_by_label("반응 이름")).to_be_disabled()
    expect(page.get_by_label("run 1 response")).to_be_enabled()
    expect(page.get_by_role("button", name="새 revision 저장")).to_be_enabled()


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


def verify_lazy_panel_direct_routes(page: Page, frontend_base_url: str) -> None:
    routes = [
        (
            "/analysis/regression/regression.linear_model",
            "회귀모형 적합 실행",
            "RegressionAnalysisPanels",
        ),
        (
            "/analysis/quality/quality.attribute_control_chart",
            "계수형 관리도 실행",
            "QualityAnalysisPanels",
        ),
        (
            "/analysis/doe/doe.factorial_design",
            "2-level full factorial 설계 생성",
            "DoeAnalysisPanels",
        ),
        (
            "/analysis/doe/doe.bayesian_optimization",
            "Bayesian 최적화",
            "DoeAnalysisPanels",
        ),
    ]
    for route_path, heading, module_name in routes:
        page.goto(f"{frontend_base_url}{route_path}", wait_until="networkidle")
        expect(page.get_by_role("heading", name=heading)).to_be_visible(timeout=15_000)
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
        page.get_by_role("button", name=re.compile(r"실험 계획법")).click()
        expect(
            page.get_by_role("heading", name="2-level full factorial 설계 생성")
        ).to_be_visible(timeout=15_000)
        expect(page.get_by_label("분석 패널 로드 오류")).to_have_count(0)
    finally:
        page.close()


def verify_doe_response_surface_analysis(page: Page) -> None:
    page.get_by_role("button", name="반응표면법 메서드 보기").click()
    expect(page.locator("#response-surface-title")).to_be_visible()

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
    analysis_button.click()

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

    page.get_by_role("button", name="새 revision으로 수정").click()
    expect(page.get_by_label("반응 이름")).to_be_disabled()
    expect(page.get_by_label("Run 1 반응")).to_be_enabled()
    page.get_by_label("Run 1 반응").fill(str(responses[0] + 0.1))
    page.get_by_role("button", name="새 revision 저장").click()
    history = page.get_by_label("RSM response revision history")
    expect(history).to_be_visible(timeout=20_000)
    expect(history).to_contain_text("r2")
    expect(history).to_contain_text("r1")


def verify_bayesian_optimization(page: Page) -> None:
    page.get_by_role("button", name="베이지안 최적화 메서드 보기").click()
    expect(page.get_by_role("heading", name="Bayesian 최적화")).to_be_visible(
        timeout=15_000
    )
    expect(
        page.get_by_text("앱은 목적함수를 실행하지 않습니다", exact=False)
    ).to_be_visible()

    page.get_by_role("button", name="제약 추가").click()
    page.get_by_label("제약 1 x 계수").fill("1")
    page.get_by_label("제약 1 우변").fill("0.75")
    page.get_by_role("button", name="Study 생성").click()
    summary = page.get_by_label("Bayesian study 상태")
    expect(summary).to_be_visible(timeout=20_000)
    expect(summary).to_contain_text("0 / 2")
    stored_constraints = page.get_by_label("Bayesian stored constraints")
    expect(stored_constraints).to_contain_text("constraint_1")
    expect(stored_constraints).to_contain_text("0.750000")
    page.get_by_label("Bayesian 전체 trial 예산").fill("5")

    page.get_by_label("Trial 1 관측값").fill("0.8")
    observation_buttons = page.get_by_role("button", name="관측 저장")
    observation_buttons.nth(0).click()
    confirmation = page.get_by_label("Trial 1 terminal action 확인")
    expect(confirmation).to_contain_text("objective 0.8")
    confirmation.get_by_role("button", name="관측 저장 확인").click()
    expect(page.get_by_label("Trial 1 관측값")).to_have_count(0, timeout=20_000)

    page.get_by_label("Trial 2 관측값").fill("1.0")
    observation_buttons.nth(1).click()
    page.get_by_label("Trial 2 terminal action 확인").get_by_role(
        "button", name="관측 저장 확인"
    ).click()
    recommendation_button = page.get_by_role("button", name="다음 실험 추천")
    expect(recommendation_button).to_be_enabled(timeout=20_000)
    recommendation_button.click()

    expect(page.get_by_role("heading", name="추천 결과")).to_be_visible(timeout=45_000)
    result_section = page.locator(
        'section[aria-labelledby="bayesian-recommendation-result-title"]'
    )
    expect(result_section.get_by_text("확인 대기", exact=True)).to_be_visible()
    expect(
        result_section.get_by_text("관측값이 아닌 다음 확인 실험 후보입니다.")
    ).to_be_visible()
    expect(page.get_by_text("추천", exact=True)).to_be_visible()
    expect(
        result_section.get_by_text("bayesian_optimization_confirmation_required")
    ).to_be_visible()
    expect(
        result_section.get_by_text("bayesian_optimization_no_global_optimum_guarantee")
    ).to_be_visible()
    recommendation_constraints = page.get_by_label(
        "Bayesian recommendation constraints"
    )
    expect(recommendation_constraints).to_contain_text("constraint_1")
    expect(recommendation_constraints).to_contain_text("충족")
    expect(
        result_section.get_by_text("전역 최적을 보장하지 않습니다", exact=False)
    ).to_be_visible()

    page.get_by_label("Trial 3 관측값").fill("0.97")
    trial_three_row = page.get_by_label("Trial 3 관측값").locator("xpath=ancestor::tr")
    trial_three_row.get_by_role("button", name="관측 저장").click()
    page.get_by_label("Trial 3 terminal action 확인").get_by_role(
        "button", name="관측 저장 확인"
    ).click()
    expect(result_section.get_by_text("관측 완료", exact=True)).to_be_visible(
        timeout=20_000
    )
    expect(result_section).to_contain_text("실제 관측값")
    expect(result_section).to_contain_text("0.970000")

    expect(recommendation_button).to_be_enabled(timeout=20_000)
    recommendation_button.click()
    trial_four_input = page.get_by_label("Trial 4 관측값")
    expect(trial_four_input).to_be_visible(timeout=45_000)
    trial_four_row = trial_four_input.locator("xpath=ancestor::tr")
    abandoned_coordinates = trial_four_row.locator("td").nth(2).inner_text()
    trial_four_row.get_by_role("button", name="Abandon", exact=True).click()
    abandon_confirmation = page.get_by_label("Trial 4 terminal action 확인")
    expect(abandon_confirmation).to_contain_text("향후 추천에서 제외")
    abandon_confirmation.get_by_role("button", name="Abandon 확인").click()
    expect(result_section.get_by_text("중단됨", exact=True)).to_be_visible(
        timeout=20_000
    )

    expect(recommendation_button).to_be_enabled(timeout=20_000)
    recommendation_button.click()
    trial_five_input = page.get_by_label("Trial 5 관측값")
    expect(trial_five_input).to_be_visible(timeout=45_000)
    trial_five_row = trial_five_input.locator("xpath=ancestor::tr")
    next_coordinates = trial_five_row.locator("td").nth(2).inner_text()
    assert next_coordinates != abandoned_coordinates
    expect(result_section.get_by_text("확인 대기", exact=True)).to_be_visible()
    expect(recommendation_button).to_be_disabled()
    expect(
        page.get_by_text("전체 trial 예산 5개에 도달", exact=False)
    ).to_be_visible()

    study_selector = page.get_by_label("저장된 Bayesian study")
    study_id = study_selector.input_value()
    page.reload(wait_until="networkidle")
    expect(page.get_by_role("heading", name="Bayesian 최적화")).to_be_visible(
        timeout=20_000
    )
    restored_selector = page.get_by_label("저장된 Bayesian study")
    expect(restored_selector.locator(f'option[value="{study_id}"]')).to_have_count(
        1, timeout=20_000
    )
    restored_selector.select_option(study_id)
    expect(page.get_by_label("Trial 5 관측값")).to_be_visible(timeout=20_000)
    expect(page.get_by_text("전체 trial 예산 5개에 도달", exact=False)).to_be_visible()
    expect(
        page.locator(
            'section[aria-labelledby="bayesian-recommendation-result-title"]'
        ).get_by_text("확인 대기", exact=True)
    ).to_be_visible()

    page.get_by_label("Trial 5 관측값").fill("0.96")
    trial_five_restored_row = page.get_by_label("Trial 5 관측값").locator(
        "xpath=ancestor::tr"
    )
    trial_five_restored_row.get_by_role("button", name="관측 저장").click()
    page.get_by_label("Trial 5 terminal action 확인").get_by_role(
        "button", name="관측 저장 확인"
    ).click()
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
    expect(page.get_by_label("Bayesian 전체 trial 예산")).to_be_disabled()
    expect(page.get_by_role("button", name="다음 실험 추천")).to_be_disabled()

    page.reload(wait_until="networkidle")
    restored_selector = page.get_by_label("저장된 Bayesian study")
    expect(restored_selector.locator(f'option[value="{study_id}"]')).to_have_count(
        1, timeout=20_000
    )
    restored_selector.select_option(study_id)
    expect(page.get_by_label("Bayesian study 종료 기록")).to_be_visible(timeout=20_000)
    expect(page.get_by_role("button", name="이 정의로 successor study 준비")).to_be_visible()
    page.get_by_role("button", name="삭제 영향 확인").click()
    deletion_impact = page.get_by_label("Bayesian study 삭제 영향")
    expect(deletion_impact).to_be_visible(timeout=20_000)
    expect(deletion_impact).to_contain_text("파일 0개")
    expect(deletion_impact).to_contain_text("recommendation 3건")
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

        page.get_by_role("button", name="데이터셋", exact=True).click()
        page.get_by_label("원본 데이터 파일").set_input_files(str(xlsx_path))
        page.get_by_role("button", name="업로드").click()
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(
            timeout=15_000
        )
        expect(page.get_by_text("browser-upload-sample.xlsx")).to_be_visible()

        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
        expect(
            page.get_by_role("heading", name=re.compile(r"Dataset version v1")),
        ).to_be_visible(timeout=20_000)
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

        page.get_by_role("button", name="데이터셋", exact=True).click()
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
        expect(
            page.get_by_role("heading", name=re.compile(r"Dataset version v1")),
        ).to_be_visible(timeout=20_000)
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

        page.get_by_role("button", name="데이터셋", exact=True).click()
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
        expect(
            page.get_by_role("heading", name=re.compile(r"Dataset version v1")),
        ).to_be_visible(timeout=20_000)
        expect_dataset_context_counts(page, row_label="2행", column_label="2컬럼")
        expect(page.get_by_role("columnheader", name="Alpha")).to_be_visible()
        expect(page.get_by_role("columnheader", name="Beta")).to_be_visible()
        expect(page.get_by_text("(missing)")).to_be_visible()
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

        page.get_by_role("button", name="데이터셋", exact=True).click()
        page.get_by_label("원본 데이터 파일").set_input_files(str(csv_path))
        page.get_by_role("button", name="업로드").click()
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(
            timeout=15_000
        )
        expect(page.get_by_text("semicolon-delimiter.csv")).to_be_visible()

        page.get_by_label("구분자").select_option(";")

        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
        expect(
            page.get_by_role("heading", name=re.compile(r"Dataset version v1")),
        ).to_be_visible(timeout=20_000)
        expect_dataset_context_counts(page, row_label="2행", column_label="2컬럼")
        expect(page.get_by_role("columnheader", name="Category")).to_be_visible()
        expect(page.get_by_role("columnheader", name="Value")).to_be_visible()
        expect(page.get_by_role("cell", name="Left", exact=True)).to_be_visible()
        expect(page.get_by_role("cell", name="20", exact=True)).to_be_visible()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def verify_xlsx_sheet_selection(page: Page, temp_dir: Path) -> None:
    try:
        xlsx_path = temp_dir / "multi-sheet-upload.xlsx"
        xlsx_path.write_bytes(multi_sheet_xlsx_workbook_bytes())

        page.get_by_role("button", name="데이터셋", exact=True).click()
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
        expect(
            page.get_by_role("heading", name=re.compile(r"Dataset version v1")),
        ).to_be_visible(timeout=20_000)
        expect_dataset_context_counts(page, row_label="2행", column_label="2컬럼")
        expect(page.get_by_role("columnheader", name="Station")).to_be_visible()
        expect(page.get_by_role("columnheader", name="Reading")).to_be_visible()
        expect(page.get_by_role("cell", name="S2", exact=True)).to_be_visible()
        expect(page.get_by_role("cell", name="43", exact=True)).to_be_visible()
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

        page.get_by_role("button", name="데이터셋", exact=True).click()
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
        expect(
            page.get_by_role("heading", name=re.compile(r"Dataset version v1")),
        ).to_be_visible(timeout=20_000)
        expect_dataset_context_counts(page, row_label="2행", column_label="2컬럼")
        expect(
            page.get_by_role("columnheader", name="이름", exact=True)
        ).to_be_visible()
        expect(page.get_by_role("columnheader", name="값", exact=True)).to_be_visible()
        expect(page.get_by_role("cell", name="홍길동", exact=True)).to_be_visible()
        expect(page.get_by_role("cell", name="김철수", exact=True)).to_be_visible()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def expect_dataset_context_counts(
    page: Page, *, row_label: str, column_label: str
) -> None:
    context_bar = page.locator('[aria-label="데이터셋 컨텍스트"]')
    expect(context_bar.get_by_text(row_label, exact=True)).to_be_visible()
    expect(context_bar.get_by_text(column_label, exact=True)).to_be_visible()


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
