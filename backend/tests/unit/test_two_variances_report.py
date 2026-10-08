import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_two_variances_api import dataset, run_body

from app.core.config import Settings
from app.main import create_app
from app.services.two_variances_report import render_two_variances_report


@pytest.mark.parametrize("locale", ["en", "ko"])
@pytest.mark.parametrize(
    "method,alternative", [("brown_forsythe", "two_sided"), ("normal_f", "greater")]
)
def test_report_exports_saved_payload_without_fit_or_rows(
    tmp_path, monkeypatch, locale, method, alternative
) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = dataset(client)
        body = run_body(version)
        body["options"].update(method=method, alternative=alternative)
        if method == "normal_f":
            body["options"]["hypothesized_ratio"] = 0.5
        created = client.post("/api/v1/analysis-runs", json=body)
        assert created.status_code == 201, created.text
        source = created.json()
        files = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in Path(tmp_path).rglob("*.json")
        }

        def fail(*args, **kwargs):
            raise AssertionError("export must not fit or read raw rows")

        monkeypatch.setattr(
            "app.services.analysis_runner_two_variances.calculate_two_variances", fail
        )
        monkeypatch.setattr(
            "app.services.analysis_runner_two_variances.iter_rows_for_snapshot", fail
        )
        monkeypatch.setattr("app.services.dataset_rows.iter_dataset_rows", fail)
        url = f"/api/v1/analysis-runs/{source['analysis_id']}/exports"
        html_export = client.post(url + "/html", json={"locale": locale})
        assert html_export.status_code == 201, html_export.text
        page = client.get(url + f"/{html_export.json()['export_id']}/download").content.decode(
            "utf-8"
        )
        visible = page.split('<section class="technical-details"')[0]
        assert 'data-two-variances-report="1"' in visible
        assert "<svg" in visible and "<table" in visible
        assert "0.25" in visible
        if locale == "en":
            assert "specified ratio hypothesis" in visible
            assert "Evidence of a variance difference." not in visible
        assert "<script" not in page and 'src="http' not in page
        assert ("두 분산 비교" if locale == "ko" else "Two Variances") in visible
        if method == "brown_forsythe":
            assert (
                "비율 신뢰구간을 제공하지" if locale == "ko" else "does not provide a ratio"
            ) in visible
        else:
            assert ("상한 없음" if locale == "ko" else "Unbounded") in visible
        for kind in ("csv", "json"):
            exported = client.post(url + "/" + kind)
            assert exported.status_code == 201, exported.text
            downloaded = client.get(url + f"/{exported.json()['export_id']}/download")
            assert downloaded.status_code == 200
        assert all(
            hashlib.sha256(path.read_bytes()).hexdigest() == digest
            for path, digest in files.items()
        )
        assert (
            client.get(f"/api/v1/analysis-runs/{source['analysis_id']}/result").json()["result"]
            == source["result"]
        )
        modified = json.loads(json.dumps(source["result"]))
        modified["groups"][0]["label"] = "<script>alert('x')</script>"
        rendered = render_two_variances_report(modified, locale)
        assert "<script>" not in rendered and "&lt;script&gt;" in rendered


def test_report_rejects_incomplete_or_unknown_schema() -> None:
    with pytest.raises(ValueError, match="schema_unsupported"):
        render_two_variances_report({"schema_version": 2}, "en")
    with pytest.raises(ValueError, match="payload_invalid"):
        render_two_variances_report(
            {"schema_version": 1, "summary_type": "two_variances_test"}, "en"
        )
