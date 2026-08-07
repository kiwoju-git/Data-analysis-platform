from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-url", required=True)
    parser.add_argument("--presentation-url", required=True)
    parser.add_argument("--diagnostics-root", required=True)
    return parser.parse_args()


def sidebar_labels(page) -> list[str]:
    return [
        label.strip()
        for label in page.locator(".sidebar-group-control > span").all_text_contents()
    ]


def main() -> int:
    args = parse_args()
    diagnostics = Path(args.diagnostics_root).resolve()
    diagnostics.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})

        full_page = context.new_page()
        full_page.goto(args.full_url, wait_until="networkidle")
        full_page.get_by_role("heading", name="Statistical Twin 대시보드").wait_for()
        full_labels = sidebar_labels(full_page)
        assert full_labels == [
            "홈",
            "데이터셋",
            "분석",
            "그래프",
            "리포트",
            "관리",
            "도움말",
        ], full_labels
        assert full_page.get_by_text("발표용 기능 미리보기").count() == 0
        full_page.screenshot(path=diagnostics / "full-home.png", full_page=True)

        presentation_page = context.new_page()
        presentation_page.goto(args.presentation_url, wait_until="networkidle")
        presentation_page.get_by_role(
            "heading", name="Statistical Twin 대시보드"
        ).wait_for()
        presentation_labels = sidebar_labels(presentation_page)
        assert presentation_labels == ["홈", "데이터셋", "분석"], presentation_labels
        presentation_page.get_by_text("발표용 기능 미리보기", exact=True).wait_for()
        presentation_page.get_by_text(
            "공개 시연 범위: 홈 · 데이터셋 · 탐색적 분석 · 가설 검정",
            exact=True,
        ).wait_for()
        assert presentation_page.locator(".home-quick-card").count() == 2
        presentation_page.screenshot(
            path=diagnostics / "presentation-home.png",
            full_page=True,
        )

        presentation_page.get_by_role("button", name="분석", exact=True).click()
        module_labels = presentation_page.locator(
            "#sidebar-submenu-analysis > li > .sidebar-submenu-button > span",
        ).all_text_contents()
        assert [label.strip() for label in module_labels] == [
            "탐색적 분석",
            "가설 검정",
        ]
        presentation_page.screenshot(
            path=diagnostics / "presentation-analysis-modules.png",
            full_page=True,
        )

        presentation_page.goto(
            f"{args.presentation_url}/manage", wait_until="networkidle"
        )
        presentation_page.get_by_role(
            "heading", name="Statistical Twin 대시보드"
        ).wait_for()
        assert presentation_page.get_by_role("heading", name="자산 관리").count() == 0

        comparison_page = context.new_page()
        comparison_page.set_viewport_size({"width": 1440, "height": 900})
        comparison_page.set_content(
            f"""
            <!doctype html><html><body style="margin:0;font-family:Arial,sans-serif">
              <h1 style="font-size:18px;margin:10px">Full 8000/8600 and Presentation 8001/8601</h1>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:8px">
                <iframe title="Full application" src="{args.full_url}" style="width:100%;height:820px;border:1px solid #888"></iframe>
                <iframe title="Presentation preview" src="{args.presentation_url}" style="width:100%;height:820px;border:1px solid #888"></iframe>
              </div>
            </body></html>
            """,
            wait_until="networkidle",
        )
        comparison_page.screenshot(
            path=diagnostics / "full-and-presentation-concurrent.png",
            full_page=True,
        )
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
