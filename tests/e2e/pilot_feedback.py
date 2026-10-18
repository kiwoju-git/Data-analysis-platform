"""Privacy-safe local feedback against the source or built app; no external send."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import Browser, expect, sync_playwright

from app_readiness import diagnosed_page, wait_for_app_ready


def verify_pilot_feedback(browser: Browser, base_url: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for locale, clipboard in (("ko", "absent"), ("en", "rejected")):
        title = (
            "문제 신고 / 의견 보내기"
            if locale == "ko"
            else "Report a Problem / Send Feedback"
        )
        labels = (
            (
                "재현 단계",
                "기대 동작",
                "실제 동작",
                "전체 내용 미리보기",
                "내용 복사",
                "JSON 저장",
                "텍스트 저장",
            )
            if locale == "ko"
            else (
                "Steps to reproduce",
                "Expected behavior",
                "Actual behavior",
                "Full content preview",
                "Copy content",
                "Save JSON",
                "Save text",
            )
        )
        value = (
            "undefined"
            if clipboard == "absent"
            else "{writeText: () => Promise.reject(new Error('PRIVATE clipboard reason'))}"
        )
        with diagnosed_page(
            browser,
            output,
            f"feedback-{locale}",
            locale=locale,
            init_script=f"Object.defineProperty(navigator, 'clipboard', {{configurable:true, value:{value}}});",
        ) as page:
            page.set_viewport_size({"width": 1440, "height": 900})
            page.route(
                "**/api/v1/dataset-versions?*",
                lambda route: route.fulfill(
                    status=422,
                    json={
                        "error": {
                            "code": "private/path?secret=RAW",
                            "message": "SECRET_SERVER_MESSAGE",
                            "correlation_id": "operator@example.invalid",
                        },
                        "rows": ["SECRET_RAW_CELL"],
                        "column_name": "SECRET_COLUMN",
                        "filename": "SECRET_FILE.csv",
                    },
                ),
                times=1,
            )
            page.goto(base_url + "/home", wait_until="domcontentloaded")
            wait_for_app_ready(page, locale, "/home")
            retry = page.locator(
                ".active-dataset-operational-row.context-bar-error button"
            )
            expect(retry).to_be_visible()
            page.context.set_offline(True)
            with page.expect_event(
                "requestfailed",
                predicate=lambda request: "/api/v1/dataset-versions?" in request.url,
            ):
                retry.click()
            expect(retry.locator("..")).to_contain_text("api_unreachable")
            requests = []
            page.on("request", lambda request: requests.append(request.url))
            opener = page.get_by_role("button", name=title, exact=True)
            opener.click()
            dialog = page.get_by_role("dialog", name=title)
            expect(dialog).to_be_visible()
            text = 'USER_AUTHORED <script>alert(1)</script> & "한글" \ue000opaque\ue001'
            for label in labels[:3]:
                dialog.get_by_label(label, exact=True).fill(text)
            # The accessible name excludes a textarea's initial JSON text node.
            preview = dialog.get_by_role("textbox", name=labels[3], exact=True)
            document = json.loads(preview.input_value())
            assert document["user_feedback"]["reproduction"] == text
            assert document["user_feedback"]["expected"] == text
            assert document["user_feedback"]["actual"] == text
            diagnostics = document["diagnostics"]
            assert diagnostics["locale"] == locale
            assert diagnostics["server_connection"] == "unreachable"
            assert diagnostics["error_code"] == "api_unreachable"
            assert diagnostics["correlation_id"] is None
            assert "SECRET" not in json.dumps(document)
            assert "USER_AUTHORED" not in json.dumps(diagnostics)
            assert page.locator("script").filter(has_text="alert(1)").count() == 0
            dialog.get_by_role("button", name=labels[4], exact=True).click()
            expect(dialog.get_by_role("status")).to_contain_text(
                "클립보드를 사용할 수 없습니다"
                if locale == "ko"
                else "Clipboard is unavailable"
            )
            expect(preview).to_be_focused()
            assert preview.evaluate(
                "node => node.selectionStart === 0 && node.selectionEnd === node.value.length"
            )
            for label, extension in ((labels[5], "json"), (labels[6], "txt")):
                with page.expect_download() as pending:
                    dialog.get_by_role("button", name=label, exact=True).click()
                downloaded = pending.value
                assert (
                    downloaded.suggested_filename
                    == f"statistical-twin-feedback.{extension}"
                )
                path = output / f"feedback-{locale}.{extension}"
                downloaded.save_as(path)
                assert json.loads(path.read_text(encoding="utf-8")) == document
            for _ in range(13):
                page.keyboard.press("Tab")
                assert dialog.evaluate("node => node.contains(document.activeElement)")
            for _ in range(13):
                page.keyboard.press("Shift+Tab")
                assert dialog.evaluate("node => node.contains(document.activeElement)")
            for width in (1440, 390):
                page.set_viewport_size(
                    {"width": width, "height": 900 if width == 1440 else 844}
                )
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth + 1"
                )
                bounds = dialog.bounding_box()
                assert (
                    bounds
                    and bounds["x"] >= 0
                    and bounds["x"] + bounds["width"] <= width + 1
                )
                page.screenshot(path=str(output / f"feedback-{locale}-{width}.png"))
            page.keyboard.press("Escape")
            expect(dialog).to_have_count(0)
            expect(opener).to_be_focused()
            assert requests == [], requests
            results.append(
                {
                    "locale": locale,
                    "clipboard": clipboard,
                    "offline": True,
                    "http_requests_after_open": 0,
                    "copy_fallback": True,
                    "json_and_text_downloads": True,
                    "focus_trap_and_restore": True,
                    "viewports": [1440, 390],
                    "catalog_error_response_injected": True,
                    "offline_failure_trigger": "visible catalog retry",
                }
            )
        with diagnosed_page(
            browser, output, f"feedback-startup-{locale}", locale=locale
        ) as page:
            page.route(
                "**/api/v1/**", lambda route: route.abort("connectionrefused")
            )
            page.goto(base_url + "/home", wait_until="domcontentloaded")
            expect(
                page.locator('.runtime-gate-page[data-runtime-state="blocked"]')
            ).to_be_visible()
            page.context.set_offline(True)
            requests = []
            page.on("request", lambda request: requests.append(request.url))
            opener = page.get_by_role("button", name=title, exact=True)
            opener.click()
            dialog = page.get_by_role("dialog", name=title)
            expect(dialog).to_be_visible()
            document = json.loads(
                dialog.get_by_role("textbox", name=labels[3], exact=True).input_value()
            )
            diagnostics = document["diagnostics"]
            assert diagnostics["app_version"] is None
            assert diagnostics["api_contract_version"] is None
            assert diagnostics["metadata_schema_version"] is None
            assert diagnostics["method_id"] is None
            assert diagnostics["server_connection"] == "unreachable"
            assert diagnostics["error_code"] == "api_unreachable"
            with page.expect_download() as pending:
                dialog.get_by_role("button", name=labels[5], exact=True).click()
            path = output / f"feedback-startup-{locale}.json"
            pending.value.save_as(path)
            assert json.loads(path.read_text(encoding="utf-8")) == document
            page.keyboard.press("Escape")
            expect(dialog).to_have_count(0)
            expect(opener).to_be_focused()
            assert requests == [], requests
            results.append(
                {
                    "locale": locale,
                    "initial_runtime_transport_failure_injected": True,
                    "all_initial_api_transports_unreachable": True,
                    "feedback_offline": True,
                    "unknown_runtime_omitted": True,
                    "http_requests_after_open": 0,
                }
            )
    (output / "feedback-evidence.json").write_text(
        json.dumps({"status": "passed", "cases": results}, indent=2), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            verify_pilot_feedback(browser, args.base_url, args.output)
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
