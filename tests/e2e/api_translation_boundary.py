"""Synthetic, black-box API/display integrity checks for source and built UI.

The caller must own an isolated workspace and its server lifecycle. This fixture
creates only synthetic datasets, never loads app source modules into the browser,
and leaves workspace cleanup to that owning runner.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Page, Request, expect

from app_readiness import diagnosed_page, wait_for_app_ready


TOKEN_TEXT = "\ue000startup.failed\ue001"
HEADERS = ["code", "message", "warnings", f'column "quote" \\ path\n{TOKEN_TEXT}']
ROWS = [
    [
        "future_warning_v9",
        f'quoted "value" \\ path\nsecond line {TOKEN_TEXT}',
        f"\uc2e4\ud589 \uc911 {TOKEN_TEXT}",
        "12.5",
    ],
    [
        "constructor",
        r"literal \\n and \\uE000startup.failed\\uE001",
        '<img src=x onerror="throw 1">',
        "13.5",
    ],
]


def synthetic_csv() -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(HEADERS)
    writer.writerows(ROWS)
    return buffer.getvalue()


def expected_paste_request() -> dict[str, str]:
    return {"content": synthetic_csv(), "original_filename": "pasted-data.txt"}


def _matches(request: Request, path: str, method: str = "POST") -> bool:
    return request.method == method and urlsplit(request.url).path == path


def _switch_locale(page: Page, locale: str) -> None:
    page.locator(".language-switcher button").filter(
        has_text="KOR" if locale == "ko" else "ENG"
    ).click()
    wait_for_app_ready(page, locale, "/datasets")


def _paste(page: Page, text: str) -> None:
    surface = page.locator(".paste-drop-surface")
    surface.focus()
    surface.evaluate(
        """(element, text) => {
          const clipboard = new DataTransfer();
          clipboard.setData('text/plain', text);
          clipboard.setData('text/html', '<b>not-the-plain-text-fixture</b>');
          element.dispatchEvent(new ClipboardEvent('paste', {
            bubbles: true, cancelable: true, clipboardData: clipboard,
          }));
        }""",
        text,
    )


def _record(path: Path, evidence: dict[str, object]) -> None:
    original_failure = sys.exc_info()[0] is not None
    try:
        path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as error:
        if not original_failure:
            raise
        print(
            f"[diagnostics] API boundary evidence failed: {type(error).__name__}",
            file=sys.stderr,
        )


def _confirm_and_verify(
    page: Page,
    base_url: str,
    upload: dict,
    locale: str,
    evidence: dict[str, object],
) -> None:
    parsing = page.locator("#dataset-parsing")
    expect(parsing).to_be_visible()
    parsing.locator("select").nth(0).select_option("utf-8")
    parsing.locator("select").nth(1).select_option(",")
    parsing.locator('input[type="checkbox"]').check()
    parsing.locator('input[type="number"]').fill("1")
    expected = {
        "parsing": {
            "kind": "delimited_text",
            "encoding": "utf-8",
            "delimiter": ",",
            "quote_char": '"',
            "decimal": ".",
            "thousands": None,
            "has_header": True,
            "header_row": 1,
            "data_start_row": 2,
            "missing_tokens": ["", "NA", "N/A", "null", "N/T"],
            "xlsx_sheet_name": None,
        },
        "columns": [],
    }
    path = f"/api/v1/datasets/{upload['dataset_id']}/confirm-parsing"
    with (
        page.expect_request(lambda request: _matches(request, path)) as requested,
        page.expect_response(
            lambda response: _matches(response.request, path)
        ) as confirmed,
        page.expect_response(
            lambda response: response.request.method == "GET"
            and urlsplit(response.url).path.startswith("/api/v1/dataset-versions/")
            and urlsplit(response.url).path.endswith("/rows")
        ) as previewed,
    ):
        parsing.locator("button.primary-button").click()
    confirm_response = confirmed.value
    evidence["confirm_request"] = requested.value.post_data_json
    evidence["confirm_status"] = confirm_response.status
    evidence["confirm_response"] = confirm_response.json()
    assert requested.value.post_data_json == expected
    assert confirm_response.status == 201
    version = confirm_response.json()
    assert version["source_sha256"] == upload["sha256"]
    assert [item["original_name"] for item in version["columns"]] == HEADERS
    assert version["row_count"] == len(ROWS)
    assert version["column_count"] == len(HEADERS)
    preview_response = previewed.value
    evidence["rows_response"] = preview_response.json()
    assert preview_response.status == 200
    preview = preview_response.json()
    assert preview["version_id"] == version["version_id"]
    assert [row["values"] for row in preview["rows"]] == ROWS

    # An independent read verifies what was stored, not only a POST response.
    stored_response = page.request.get(
        f"{base_url}/api/v1/dataset-versions/{version['version_id']}"
    )
    assert stored_response.status == 200
    stored_version = stored_response.json()
    assert stored_version["columns"] == version["columns"]
    assert stored_version["source_sha256"] == upload["sha256"]
    stored_rows = page.request.get(
        f"{base_url}/api/v1/dataset-versions/{version['version_id']}/rows?offset=0&limit=10"
    )
    assert stored_rows.status == 200
    assert [row["values"] for row in stored_rows.json()["rows"]] == ROWS

    schema_rows = page.locator(".schema-table tbody tr")
    expect(schema_rows).to_have_count(len(HEADERS))
    for index, header in enumerate(HEADERS):
        original_name = schema_rows.nth(index).locator("td").nth(0)
        expect(original_name).to_be_visible()
        assert original_name.text_content() == header
        expect(schema_rows.nth(index).locator("input").nth(0)).to_have_value(
            version["columns"][index]["display_name"]
        )
    cells = page.locator(".canonical-preview-grid .canonical-cell-text")
    expect(cells).to_have_count(len(ROWS) * len(HEADERS))
    assert cells.all_text_contents() == [value for row in ROWS for value in row]
    expect(page.locator('.canonical-preview-grid img[src="x"]')).to_have_count(0)

    # Existing server display-name sanitation is intentionally distinct from
    # original_name/raw values. Locale must not mutate an unsaved user draft.
    draft = f'draft "quote" \\ {TOKEN_TEXT} \uc0ac\uc6a9\uc790'
    name_input = schema_rows.nth(0).locator("input").nth(0)
    name_input.fill(draft)
    other = "ko" if locale == "en" else "en"
    for selected_locale in (other, locale):
        _switch_locale(page, selected_locale)
        expect(name_input).to_have_value(draft)
        assert schema_rows.nth(3).locator("td").nth(0).text_content() == HEADERS[3]
        assert cells.all_text_contents() == [value for row in ROWS for value in row]
    unchanged = page.request.get(
        f"{base_url}/api/v1/dataset-versions/{version['version_id']}"
    )
    assert unchanged.status == 200
    assert unchanged.json() == stored_version
    evidence["version_id"] = version["version_id"]
    evidence["original_header_policy"] = (
        "original_name retained; existing display_name sanitation unchanged"
    )
    evidence["schema_hash_unchanged_after_locale_switch"] = stored_version[
        "schema_hash"
    ]


def verify_api_translation_boundary(
    browser: Browser,
    base_url: str,
    root: Path,
    *,
    isolated_workspace: bool,
) -> list[dict[str, object]]:
    """Run only against the owning runner's synthetic temporary workspace."""
    if not isolated_workspace:
        raise ValueError("API boundary fixture requires an isolated workspace")
    endpoint = urlsplit(base_url)
    if endpoint.scheme != "http" or endpoint.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("API boundary fixture requires a local test server")
    base_url = base_url.rstrip("/")
    payload = synthetic_csv().encode("utf-8")
    expected_sha = hashlib.sha256(payload).hexdigest()
    summaries = []
    for locale in ("en", "ko"):
        for mode in ("paste", "upload"):
            stage = f"{mode}-{locale}"
            evidence: dict[str, object] = {
                "fixture": "synthetic",
                "locale": locale,
                "mode": mode,
                "expected_source_sha256": expected_sha,
                "expected_headers": HEADERS,
                "expected_rows": ROWS,
                "status": "incomplete",
            }
            with diagnosed_page(browser, root, stage, locale=locale) as page:
                try:
                    page.goto(base_url + "/datasets", wait_until="domcontentloaded")
                    wait_for_app_ready(page, locale, "/datasets")
                    path = (
                        "/api/v1/datasets/paste"
                        if mode == "paste"
                        else "/api/v1/datasets"
                    )
                    if mode == "paste":
                        expected = expected_paste_request()
                        evidence["expected_request"] = expected
                        _paste(page, expected["content"])
                        raw = page.locator(".raw-paste-control textarea")
                        expect(raw).to_have_value(
                            expected["content"].replace("\r\n", "\n")
                        )
                        _switch_locale(page, "ko" if locale == "en" else "en")
                        expect(raw).to_have_value(
                            expected["content"].replace("\r\n", "\n")
                        )
                        _switch_locale(page, locale)
                        submit = page.locator('.paste-panel button[type="submit"]')
                    else:
                        page.locator(
                            '.upload-panel input[type="file"]'
                        ).set_input_files(
                            {
                                "name": f"boundary-{locale}.csv",
                                "mimeType": "text/csv",
                                "buffer": payload,
                            }
                        )
                        submit = page.locator('.upload-panel button[type="submit"]')
                    with (
                        page.expect_request(
                            lambda request: _matches(request, path)
                        ) as requested,
                        page.expect_response(
                            lambda response: _matches(response.request, path)
                        ) as received,
                    ):
                        submit.click()
                    request = requested.value
                    response = received.value
                    evidence["request_content_type"] = request.headers.get(
                        "content-type"
                    )
                    evidence["request_accept_language"] = request.headers.get(
                        "accept-language"
                    )
                    evidence["response_status"] = response.status
                    evidence["response"] = response.json()
                    assert request.headers.get("accept-language") == locale
                    assert response.status == 201
                    if mode == "paste":
                        evidence["actual_request_body"] = request.post_data
                        assert request.post_data == json.dumps(
                            expected, ensure_ascii=False, separators=(",", ":")
                        )
                        assert request.post_data_json == expected
                    else:
                        assert request.headers["content-type"].startswith(
                            "multipart/form-data;"
                        )
                    upload = response.json()
                    assert upload["sha256"] == expected_sha
                    assert upload["size_bytes"] == len(payload)
                    _confirm_and_verify(page, base_url, upload, locale, evidence)
                    page.screenshot(
                        path=str(root / stage / "stored-values.png"), full_page=True
                    )
                    evidence["status"] = "passed"
                    summaries.append(
                        {
                            "stage": stage,
                            "source_sha256": expected_sha,
                            "version_id": evidence["version_id"],
                            "status": "passed",
                        }
                    )
                finally:
                    _record(root / stage / "boundary-evidence.json", evidence)
    return summaries
