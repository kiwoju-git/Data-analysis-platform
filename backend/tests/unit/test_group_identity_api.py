"""Current identities and genuine legacy-shaped stored envelopes use read-only exports."""

import hashlib
import json
import sqlite3
from html import escape
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.analyses.registry import METHOD_VERSIONS
from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import (
    get_analysis_artifact_record,
    get_analysis_run_record,
    metadata_db_path,
)


@pytest.mark.parametrize(
    ("method", "schema", "legacy"),
    [
        ("eda.equal_variances", 3, False),
        ("hypothesis.two_sample_t", 2, False),
        ("hypothesis.kruskal_wallis", 2, False),
        ("eda.equal_variances", 1, True),
        ("eda.equal_variances", 2, True),
        ("hypothesis.two_sample_t", 1, True),
        ("hypothesis.kruskal_wallis", 1, True),
    ],
)
def test_group_identity_api_restore_report_and_legacy_bytes(
    tmp_path: Path, method: str, schema: int, legacy: bool
) -> None:
    settings = Settings(workspace_root=tmp_path)
    prefix = "X" * 121
    names = [prefix + "-A<&>", prefix + "-B", "C", "D"]
    if method == "hypothesis.two_sample_t":
        names = names[:2]
    csv = "response,group\n" + "".join(
        f"{index * 10 + value},{name}\n"
        for index, name in enumerate(names)
        for value in range(1, 6)
    )
    with TestClient(create_app(settings)) as client:
        upload = client.post(
            "/api/v1/datasets", files={"file": ("groups.csv", csv.encode(), "text/csv")}
        )
        assert upload.status_code == 201
        confirmed = client.post(
            f"/api/v1/datasets/{upload.json()['dataset_id']}/confirm-parsing",
            json={
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
                    "missing_tokens": [""],
                },
                "columns": [],
            },
        )
        assert confirmed.status_code == 201
        version = confirmed.json()
        response_id, group_id = [column["column_id"] for column in version["columns"]]
        created = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": method,
                "method_version": METHOD_VERSIONS[method],
                "dataset_version_id": version["version_id"],
                "roles": {"response": response_id, "group": group_id},
                "options": {"response_column_id": response_id, "group_column_id": group_id},
            },
        )
        assert created.status_code == 201, created.text
        envelope = created.json()
        analysis_id = envelope["analysis_id"]
        record = get_analysis_run_record(tmp_path, analysis_id)
        assert record is not None and record.result_path is not None
        source = tmp_path / record.result_path
        assert [group["n"] for group in envelope["result"]["groups"]] == [5] * len(names)
        assert [group["group_value"] for group in envelope["result"]["groups"]] == names
        if legacy:
            # Construct a legacy fixture only in this new synthetic workspace.
            def strip_new_identity(value: object) -> None:
                if isinstance(value, dict):
                    for key in tuple(value):
                        if key in {
                            "group_value",
                            "group_1_value",
                            "group_2_value",
                            "group_1_index",
                            "group_2_index",
                            "left_group_index",
                            "right_group_index",
                            "left_group_value",
                            "right_group_value",
                        }:
                            del value[key]
                        else:
                            strip_new_identity(value[key])
                elif isinstance(value, list):
                    for item in value:
                        strip_new_identity(item)

            strip_new_identity(envelope["result"])
            envelope["result"]["schema_version"] = schema
            envelope["method_version"] = "0.2.0" if method == "eda.equal_variances" else "0.1.0"
            envelope["provenance"]["method_version"] = envelope["method_version"]
            config = json.loads(record.config_json)
            config["method_version"] = envelope["method_version"]
            if method == "eda.equal_variances" and schema == 1:
                for key in ("multiple_comparisons", "levene", "additional_tests"):
                    envelope["result"].pop(key, None)
            raw = json.dumps(envelope, ensure_ascii=False).encode()
            source.write_bytes(raw)
            with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
                connection.execute(
                    "UPDATE analysis_runs SET result_sha256 = ?, method_version = ?, "
                    "config_json = ? WHERE analysis_id = ?",
                    (
                        hashlib.sha256(raw).hexdigest(),
                        envelope["method_version"],
                        json.dumps(config),
                        analysis_id,
                    ),
                )
        else:
            assert envelope["result"]["schema_version"] == schema
        before = source.read_bytes()
        restored = client.get(f"/api/v1/analysis-runs/{analysis_id}/result")
        assert restored.status_code == 200
        assert restored.json() == envelope
        for locale in ("ko", "en"):
            report = client.post(
                f"/api/v1/analysis-runs/{analysis_id}/exports/html", json={"locale": locale}
            )
            assert report.status_code == 201, report.text
            artifact = get_analysis_artifact_record(
                tmp_path, analysis_id, report.json()["export_id"]
            )
            assert artifact is not None
            html = (tmp_path / artifact.path).read_text(encoding="utf-8")
            if legacy:
                assert (
                    "전체 그룹값이 없습니다"
                    if locale == "ko"
                    else "does not contain full group values"
                ) in html
            else:
                for name in names:
                    assert f"<td>{escape(name)}</td>" in html
            assert source.read_bytes() == before
            assert (
                hashlib.sha256(before).hexdigest()
                == get_analysis_run_record(tmp_path, analysis_id).result_sha256
            )
