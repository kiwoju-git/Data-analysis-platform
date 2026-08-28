from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-url", required=True)
    parser.add_argument("--preview-url", required=True)
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
        context.add_init_script(
            "window.localStorage.setItem('statistical-twin.locale', 'ko')"
        )

        full_page = context.new_page()
        full_page.goto(args.full_url, wait_until="networkidle")
        full_page.get_by_role("heading", name="Statistical Twin 대시보드").wait_for()
        assert sidebar_labels(full_page) == [
            "홈",
            "데이터셋",
            "분석",
            "그래프",
            "리포트",
            "관리",
            "도움말",
        ]

        preview_page = context.new_page()
        preview_page.goto(args.preview_url, wait_until="networkidle")
        preview_page.get_by_role("heading", name="Statistical Twin 대시보드").wait_for()
        assert sidebar_labels(preview_page) == ["홈", "데이터셋", "분석"]
        preview_page.get_by_text("발표용 기능 미리보기", exact=True).wait_for()
        preview_page.goto(f"{args.preview_url}/analysis", wait_until="networkidle")

        cards = preview_page.locator(".analysis-domain-card")
        assert cards.count() == 8
        assert preview_page.locator("button.analysis-domain-card").count() == 4
        assert (
            preview_page.locator("article.analysis-domain-card.is-planned").count() == 4
        )
        expected_domains = [
            "기초통계·탐색",
            "평균비교·동등성",
            "비율·범주형 데이터",
            "상관·회귀·예측",
            "실험계획·최적화",
            "AI/ML 실험설계",
            "품질·공정 모니터링",
            "측정시스템·변동성",
        ]
        assert cards.locator("strong").all_text_contents() == expected_domains

        preview_page.get_by_role("button", name="분석", exact=True).click()
        domain_buttons = preview_page.locator(
            "#sidebar-submenu-analysis > li > .sidebar-submenu-button"
        )
        assert domain_buttons.count() == 8
        for index in range(4):
            assert domain_buttons.nth(index).is_enabled()
        for index in range(4, 8):
            assert domain_buttons.nth(index).is_disabled()

        preview_page.screenshot(
            path=diagnostics / "presentation-four-domains-analysis.png",
            full_page=True,
        )

        comparison_page = context.new_page()
        comparison_page.set_viewport_size({"width": 1920, "height": 900})
        comparison_page.set_content(
            f"""
            <!doctype html><html><body style="margin:0;font-family:Arial,sans-serif">
              <h1 style="font-size:18px;margin:10px">Full and four-domain preview</h1>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:8px">
                <iframe title="Full application" src="{args.full_url}" style="width:100%;height:820px;border:1px solid #888"></iframe>
                <iframe title="Four-domain preview" src="{args.preview_url}" style="width:100%;height:820px;border:1px solid #888"></iframe>
              </div>
            </body></html>
            """,
            wait_until="networkidle",
        )
        comparison_page.screenshot(
            path=diagnostics / "full-and-four-domain-preview-concurrent.png",
            full_page=True,
        )
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
