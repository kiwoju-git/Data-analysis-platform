"""Synthetic built-app field validation; never creates a study or fits a model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from app_readiness import diagnosed_page
from bo_capacity import fill_import


def verify_import_fields(browser, base, output, *, isolated_workspace):
    if not isolated_workspace:
        raise ValueError("Use an isolated synthetic workspace")
    output.mkdir(parents=True, exist_ok=True)
    with diagnosed_page(
        browser,
        output,
        "import-field-validation",
        init_script="localStorage.setItem('statistical-twin.locale','en')",
    ) as page:
        errors, posts = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: posts.append(request.url)
            if request.method == "POST" and "/bayesian-studies/" in request.url
            else None,
        )
        form, source_hash = fill_import(page, base, 12)
        form = page.locator(".bo-dataset-import")
        name = form.get_by_label("Import study name", exact=True)
        target = form.get_by_label("Response 2 target", exact=True)
        name.fill("")
        target.fill("")
        form.get_by_role("button", name="Preflight import", exact=True).click()
        expect(name).to_have_attribute("aria-invalid", "true")
        expect(target).to_have_attribute("aria-invalid", "true")
        expect(name).to_be_focused()
        expect(
            form.locator(".bo-import-field-error").filter(has_text="Enter a value.")
        ).to_have_count(2)
        assert posts == []
        summary = form.locator(".bo-import-validation-summary")
        summary.get_by_role("link", name="Response 2 target: Enter a value.").click()
        expect(target).to_be_focused()
        before_url = page.url
        target.fill("1e")
        expect(target).to_have_value("1e")
        expect(target).to_be_focused()
        expect(
            form.locator(".bo-import-field-error").filter(
                has_text="Enter a complete, finite number"
            )
        ).to_have_count(1)
        target.fill("120")
        expect(target).not_to_have_attribute("aria-invalid", "true")
        name.fill("합성 검증 study")
        expect(summary).to_have_count(0)

        low = form.get_by_label("X 1 low", exact=True)
        high = form.get_by_label("X 1 high", exact=True)
        low.fill("30")
        expect(low).to_have_attribute("aria-invalid", "true")
        expect(high).to_have_attribute("aria-invalid", "true")
        for width in (1024, 1440):
            page.set_viewport_size({"width": width, "height": 960})
            low.scroll_into_view_if_needed()
            assert form.evaluate("""root => [...root.querySelectorAll('[aria-invalid="true"]')].every(input => {
                const error = document.getElementById(input.getAttribute('aria-describedby'));
                if (!error) return false;
                const a = input.getBoundingClientRect(), b = error.getBoundingClientRect();
                return b.top >= a.bottom + 2 && b.width > 0 && b.height > 0;
            })""")
            assert page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth + 1"
            )
            page.screenshot(path=str(output / f"fields-en-{width}.png"))
        page.get_by_role("button", name="Korean", exact=True).click()
        expect(low).to_have_value("30")
        expect(
            form.locator(".bo-import-field-error").filter(
                has_text="하한은 상한보다 작아야 합니다."
            )
        ).to_have_count(2)
        expect(form.get_by_label("반응 2 목표값", exact=True)).to_have_value("120")
        expect(form.get_by_label("가져오기 Study 이름", exact=True)).to_have_value(
            "합성 검증 study"
        )
        page.screenshot(path=str(output / "fields-ko.png"))
        page.get_by_role("button", name="영어", exact=True).click()
        low.fill("10")
        expect(summary).to_have_count(0)
        assert posts == [] and page.url == before_url

        form.get_by_text("Advanced options", exact=True).click()
        form.get_by_role("button", name="Add constraint", exact=True).click()
        form.get_by_label("Coefficient constraint_1 factor_1", exact=True).fill("1")
        form.get_by_label("Bound constraint_1", exact=True).fill("25")
        response_column = form.get_by_label("Y 1", exact=True)
        original_column = response_column.input_value()
        response_column.select_option(
            form.get_by_label("X 1", exact=True).input_value()
        )
        form.get_by_role("button", name="Preflight import", exact=True).click()
        expect(form.get_by_label("X 1", exact=True)).to_be_disabled()
        expect(response_column).to_be_focused()
        expect(summary.get_by_role("link", name="X 1 Column:")).to_have_count(0)
        expect(summary).to_contain_text("constraint coefficients before changing")
        assert posts == []
        response_column.select_option(original_column)
        expect(summary).to_have_count(0)

        with page.expect_response("**/bayesian-studies/import-preflight") as response:
            form.get_by_role("button", name="Preflight import", exact=True).click()
        assert response.value.status == 200
        assert response.value.json()["n_used"] == 12
        assert len(posts) == 1
        assert not errors, errors
        (output / "result.json").write_text(
            json.dumps(
                {
                    "synthetic": True,
                    "n": 12,
                    "source_sha256": source_hash,
                    "preflight_posts": len(posts),
                    "study_created": False,
                    "pageerrors": errors,
                    "locales": ["en", "ko"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--isolated-workspace", action="store_true")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            verify_import_fields(
                browser,
                args.base_url,
                args.output,
                isolated_workspace=args.isolated_workspace,
            )
        finally:
            browser.close()
