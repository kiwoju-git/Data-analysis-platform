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
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect, sync_playwright


SAMPLE_DATA = """Group\tValue
A\t10
A\t11
A\t12
B\t15
B\t16
B\t17
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the DataLab Studio critical-path browser E2E smoke test.",
    )
    parser.add_argument("--backend-port", type=int, default=8011)
    parser.add_argument("--frontend-port", type=int, default=5199)
    parser.add_argument("--workspace-root", type=Path, default=None)
    parser.add_argument("--keep-workspace", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    if args.workspace_root is None:
        workspace_root = Path(tempfile.mkdtemp(prefix="datalab-e2e-"))
    else:
        args.workspace_root.mkdir(parents=True, exist_ok=True)
        workspace_root = Path(tempfile.mkdtemp(prefix="run-", dir=args.workspace_root))
    log_root = workspace_root / "logs"
    log_root.mkdir(parents=True, exist_ok=True)
    processes: list[subprocess.Popen[bytes]] = []
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

        backend_log = (log_root / "backend.log").open("wb")
        frontend_log = (log_root / "frontend.log").open("wb")
        log_handles.extend([backend_log, frontend_log])

        processes.append(
            subprocess.Popen(
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
            ),
        )
        processes.append(
            subprocess.Popen(
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
            ),
        )

        wait_for_url(f"{backend_base_url}/api/v1/health", "backend health", processes)
        wait_for_url(frontend_base_url, "frontend dev server", processes)
        run_browser_flow(frontend_base_url)
        print("E2E critical path passed")
        return 0
    except Exception as exc:
        print(f"E2E critical path failed: {exc}", file=sys.stderr)
        print_recent_logs(log_root)
        return 1
    finally:
        for process in processes:
            terminate_process(process)
        for handle in log_handles:
            handle.close()
        if args.keep_workspace:
            print(f"Kept E2E workspace: {workspace_root}")
        else:
            shutil.rmtree(workspace_root, ignore_errors=True)


def npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def wait_for_url(
    url: str,
    label: str,
    processes: Sequence[subprocess.Popen[bytes]],
    timeout_seconds: float = 60.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        for process in processes:
            return_code = process.poll()
            if return_code is not None:
                raise RuntimeError(f"{label} dependency exited early with {return_code}")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
        time.sleep(0.5)
    raise TimeoutError(f"{label} did not become ready at {url}: {last_error}")


def run_browser_flow(frontend_base_url: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            page.goto(frontend_base_url, wait_until="networkidle")

            expect(page.get_by_text("DataLab Studio")).to_be_visible()
            expect(page.get_by_text("API ready")).to_be_visible(timeout=15_000)

            page.get_by_label("복사한 표 붙여넣기").fill(SAMPLE_DATA)
            page.get_by_role("button", name="붙여넣기 데이터 등록").click()
            expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)

            page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
            expect(
                page.get_by_role("heading", name=re.compile(r"Dataset version v1")),
            ).to_be_visible(timeout=20_000)
            expect_dataset_context_counts(page, row_label="6행", column_label="2컬럼")

            page.get_by_role("button", name="분석", exact=True).click()
            expect(page.get_by_role("heading", name="기술통계 실행")).to_be_visible()
            page.get_by_role("button", name="기술통계 실행").click()
            expect(page.locator(".result-table").filter(has_text="Value")).to_be_visible(
                timeout=20_000,
            )

            page.get_by_role("button", name=re.compile(r"2-표본 t-검정 메서드 보기")).click()
            expect(page.get_by_role("heading", name="2-표본 t-검정 실행")).to_be_visible()
            page.get_by_role("button", name="2-표본 t-검정 실행").click()
            expect(page.locator(".result-table").filter(has_text="Hedges g")).to_be_visible(
                timeout=20_000,
            )

            create_exports(page)
            restore_and_compare_saved_results(page)
            verify_schema_stale_behavior(page)
            verify_xlsx_file_upload(page, Path(tempfile.mkdtemp(prefix="datalab-e2e-upload-")))
            verify_csv_file_upload_and_error_recovery(
                page,
                Path(tempfile.mkdtemp(prefix="datalab-e2e-csv-upload-")),
            )
            verify_parser_option_editing(
                page,
                Path(tempfile.mkdtemp(prefix="datalab-e2e-parser-options-")),
            )
            verify_delimiter_option_editing(
                page,
                Path(tempfile.mkdtemp(prefix="datalab-e2e-delimiter-options-")),
            )
            verify_xlsx_sheet_selection(
                page,
                Path(tempfile.mkdtemp(prefix="datalab-e2e-xlsx-sheet-")),
            )
            verify_text_encoding_selection(
                page,
                Path(tempfile.mkdtemp(prefix="datalab-e2e-encoding-options-")),
            )
        finally:
            browser.close()


def create_exports(page: Page) -> None:
    page.get_by_role("button", name="JSON 생성").click()
    expect(page.get_by_role("button", name="JSON 다운로드")).to_be_visible(timeout=15_000)

    page.get_by_role("button", name="CSV 생성").click()
    expect(page.get_by_role("button", name="CSV 다운로드")).to_be_visible(timeout=15_000)

    page.get_by_role("button", name="HTML 생성").click()
    expect(page.get_by_role("button", name="HTML 다운로드")).to_be_visible(timeout=15_000)
    expect(page.get_by_text("최근 export")).to_be_visible()

    try:
        with page.expect_download(timeout=10_000) as download_info:
            page.get_by_role("button", name="JSON 다운로드").click()
        download = download_info.value
        if not download.suggested_filename.endswith(".json"):
            raise AssertionError(f"unexpected JSON download name: {download.suggested_filename}")
    except PlaywrightTimeoutError as exc:
        raise AssertionError("JSON export download did not start") from exc


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
    expect(page.get_by_text("같은 method/version일 때만 자세한 비교가 가능합니다.")).to_be_visible()
    expect(page.get_by_text(re.compile(r"method (same|different)"))).to_be_visible()


def verify_schema_stale_behavior(page: Page) -> None:
    page.get_by_role("button", name="데이터셋", exact=True).click()
    expect(
        page.get_by_role("heading", name=re.compile(r"Dataset version v1")),
    ).to_be_visible(timeout=15_000)

    page.get_by_role("button", name="스키마 저장").click()
    expect(page.get_by_role("button", name="스키마 저장")).to_be_enabled(timeout=15_000)

    page.get_by_role("button", name="분석", exact=True).click()
    expect(page.get_by_text("현재 데이터셋의 저장된 분석")).to_be_visible(timeout=15_000)
    page.get_by_role("button", name="새로고침").click()
    expect(page.locator(".analysis-history-item")).to_have_count(2, timeout=15_000)
    expect(page.locator(".analysis-history-panel .stale-badge")).to_have_count(0)

    page.get_by_role("button", name="데이터셋", exact=True).click()
    value_display_input = page.get_by_label("Value 표시명")
    value_display_input.fill("Measurement Value")
    page.get_by_role("button", name="스키마 저장").click()
    expect(value_display_input).to_have_value("Measurement Value", timeout=15_000)

    page.get_by_role("button", name="분석", exact=True).click()
    page.get_by_role("button", name="새로고침").click()
    expect(page.locator(".analysis-history-item")).to_have_count(2, timeout=15_000)
    expect(page.locator(".analysis-history-panel .stale-badge")).to_have_count(2)
    expect(page.get_by_text("stale · 재검토 필요").first).to_be_visible()


def verify_xlsx_file_upload(page: Page, temp_dir: Path) -> None:
    try:
        xlsx_path = temp_dir / "browser-upload-sample.xlsx"
        xlsx_path.write_bytes(minimal_xlsx_workbook_bytes())

        page.get_by_role("button", name="데이터셋", exact=True).click()
        page.get_by_label("원본 데이터 파일").set_input_files(str(xlsx_path))
        page.get_by_role("button", name="업로드").click()
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
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
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
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
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
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
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
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
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
        expect(page.get_by_text("multi-sheet-upload.xlsx")).to_be_visible()

        page.get_by_label("시트명").fill("Missing")
        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
        expect(page.get_by_role("alert")).to_contain_text("xlsx_sheet_not_found", timeout=15_000)
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
            (
                ("A" * 8300)
                + "\n"
                + "이름,값\n"
                + "홍길동,1\n"
                + "김철수,2\n"
            ).encode("cp949"),
        )

        page.get_by_role("button", name="데이터셋", exact=True).click()
        page.get_by_label("원본 데이터 파일").set_input_files(str(csv_path))
        page.get_by_role("button", name="업로드").click()
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible(timeout=15_000)
        expect(page.get_by_text("cp949-upload.csv")).to_be_visible()

        page.get_by_label("구분자").select_option(",")
        page.get_by_label("첫 데이터 행을 헤더로 사용").check()
        page.get_by_label("헤더 행").fill("2")
        page.get_by_label("인코딩").select_option("utf-8")
        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
        expect(page.get_by_role("alert")).to_contain_text("text_decoding_failed", timeout=15_000)
        expect(page.get_by_role("heading", name="파싱 옵션")).to_be_visible()

        page.get_by_label("인코딩").select_option("cp949")

        page.get_by_role("button", name="파싱 확정 및 버전 생성").click()
        expect(
            page.get_by_role("heading", name=re.compile(r"Dataset version v1")),
        ).to_be_visible(timeout=20_000)
        expect_dataset_context_counts(page, row_label="2행", column_label="2컬럼")
        expect(page.get_by_role("columnheader", name="이름", exact=True)).to_be_visible()
        expect(page.get_by_role("columnheader", name="값", exact=True)).to_be_visible()
        expect(page.get_by_role("cell", name="홍길동", exact=True)).to_be_visible()
        expect(page.get_by_role("cell", name="김철수", exact=True)).to_be_visible()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def expect_dataset_context_counts(page: Page, *, row_label: str, column_label: str) -> None:
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


def print_recent_logs(log_root: Path, max_bytes: int = 8000) -> None:
    for log_path in sorted(log_root.glob("*.log")):
        print(f"\n--- {log_path.name} tail ---", file=sys.stderr)
        try:
            data = log_path.read_bytes()
        except OSError as exc:
            print(f"could not read log: {exc}", file=sys.stderr)
            continue
        tail = data[-max_bytes:]
        print(tail.decode("utf-8", errors="replace"), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
