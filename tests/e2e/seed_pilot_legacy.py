"""Verification-only provisioning of new legacy records in an EMPTY workspace.

Run with the installed release interpreter (-I -B); no repository import bootstrap,
fit, SQL update, or existing-record rewrite is performed. Fixed UUID injection is
limited to test setup of newly created columns, before normal immutable writers.
"""

import argparse
import csv
import hashlib
import io
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

BASE_SHA = "0849aaa279e34a612c5c65d350cfccf220fe581e"


def canonical_payload(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def seed_legacy(workspace_root: Path, fixture_path: Path) -> dict[str, object]:
    if workspace_root.is_symlink() or (
        workspace_root.exists() and any(workspace_root.iterdir())
    ):
        raise ValueError("legacy_seed_requires_empty_workspace")
    fixture_bytes = fixture_path.read_bytes()
    if len(fixture_bytes) > 256 * 1024:
        raise ValueError("legacy_seed_fixture_too_large")
    fixture = json.loads(fixture_bytes)
    if (
        fixture.get("fixture_schema_version") != 1
        or fixture.get("source_commit") != BASE_SHA
    ):
        raise ValueError("legacy_seed_fixture_identity_mismatch")
    cases = fixture.get("cases")
    expected = {
        "eda.equal_variances": ("0.2.0", 2),
        "hypothesis.two_sample_t": ("0.1.0", 1),
        "hypothesis.kruskal_wallis": ("0.1.0", 1),
    }
    if (
        not isinstance(cases, list)
        or len(cases) != 3
        or {case["method_id"] for case in cases} != set(expected)
    ):
        raise ValueError("legacy_seed_fixture_cases_mismatch")
    for case in cases:
        if (case["method_version"], case["result"]["schema_version"]) != expected[
            case["method_id"]
        ] or hashlib.sha256(canonical_payload(case["result"])).hexdigest() != case[
            "result_sha256"
        ]:
            raise ValueError("legacy_seed_fixture_digest_mismatch")
        for key in ("response", "group"):
            UUID(case["result"][key]["column_id"])

    from app.api.v1.schemas.analyses import AnalysisRunRequest
    from app.api.v1.schemas.datasets import (
        DatasetParsingConfirmationRequest,
        PastedDatasetRequest,
    )
    from app.core.config import Settings
    from app.services import dataset_versions
    from app.services.analysis_run_execution import (
        create_row_snapshot_artifact,
        store_succeeded_analysis_result,
        utc_now,
    )
    from app.services.dataset_rows import get_dataset_rows_context
    from app.services.dataset_upload import create_dataset_from_pasted_text
    from app.storage.metadata import (
        SCHEMA_VERSION,
        get_analysis_run_record,
        initialize_metadata_store,
    )
    from app.storage.workspace_lease import acquire_workspace_lease

    settings = Settings(workspace_root=workspace_root.resolve())
    receipts = []
    with acquire_workspace_lease(settings.workspace_root):
        initialize_metadata_store(settings.workspace_root)
        for case in cases:
            result = case["result"]
            buffer = io.StringIO(newline="")
            writer = csv.writer(buffer)
            writer.writerow(["response", "group"])
            writer.writerows(case["input_rows"])
            upload = create_dataset_from_pasted_text(
                PastedDatasetRequest(
                    content=buffer.getvalue(),
                    original_filename=f"legacy-{case['method_id']}.csv",
                ),
                settings,
            )
            original_builder = dataset_versions._build_column_records
            fixed_ids = [result[key]["column_id"] for key in ("response", "group")]

            def build_fixture_columns(*args: object, **kwargs: object) -> list[object]:
                columns = original_builder(*args, **kwargs)
                if len(columns) != 2:
                    raise ValueError("legacy_seed_column_count_mismatch")
                return [
                    replace(column, column_id=identity)
                    for column, identity in zip(columns, fixed_ids, strict=True)
                ]

            confirmation = DatasetParsingConfirmationRequest.model_validate(
                {
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
                    "columns": [
                        {
                            "column_index": 0,
                            "data_type": "decimal",
                            "measurement_level": "continuous",
                            "role": "response",
                        },
                        {
                            "column_index": 1,
                            "data_type": "text",
                            "measurement_level": "nominal",
                            "role": "group",
                        },
                    ],
                }
            )
            with patch.object(
                dataset_versions, "_build_column_records", build_fixture_columns
            ):
                version = dataset_versions.confirm_dataset_parsing(
                    settings, upload.dataset_id, confirmation
                )
            context = get_dataset_rows_context(settings, version.version_id)
            request = AnalysisRunRequest(
                method_id=case["method_id"],
                method_version=case["method_version"],
                dataset_version_id=version.version_id,
                roles={"response": fixed_ids[0], "group": fixed_ids[1]},
                options={
                    "response_column_id": fixed_ids[0],
                    "group_column_id": fixed_ids[1],
                },
            )
            analysis_id = uuid4()
            created_at = utc_now()
            snapshot = create_row_snapshot_artifact(
                settings=settings,
                analysis_id=str(analysis_id),
                context=context,
                filter_snapshot=request.filter_snapshot,
                created_at=created_at,
            )
            envelope = store_succeeded_analysis_result(
                settings=settings,
                request=request,
                context=context,
                analysis_id=analysis_id,
                completed_at=created_at,
                row_snapshot=snapshot,
                result=result,
                warnings=[],
            )
            record = get_analysis_run_record(settings.workspace_root, str(analysis_id))
            assert record is not None and record.result_path is not None
            artifact_bytes = (settings.workspace_root / record.result_path).read_bytes()
            payload_digest = hashlib.sha256(
                canonical_payload(envelope.result)
            ).hexdigest()
            if payload_digest != case["result_sha256"]:
                raise ValueError("legacy_seed_result_changed")
            receipts.append(
                {
                    "analysis_id": str(analysis_id),
                    "dataset_version_id": str(version.version_id),
                    "method_id": case["method_id"],
                    "method_version": case["method_version"],
                    "result_schema_version": result["schema_version"],
                    "result_payload_sha256": payload_digest,
                    "artifact_file_sha256": hashlib.sha256(artifact_bytes).hexdigest(),
                    "source_commit": BASE_SHA,
                    "source_file_sha256": case["source_file_sha256"],
                    "group_count": result["group_count"],
                }
            )
    return {
        "schema_version": 1,
        "status": "seeded_new_workspace",
        "metadata_schema_version": SCHEMA_VERSION,
        "source_commit": BASE_SHA,
        "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "identity_setup": "verification_only_fixed_column_uuids_before_first_storage",
        "existing_records_modified": False,
        "analysis_calculations_executed": 0,
        "cases": receipts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", "--workspace", required=True, type=Path)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("legacy_seed_receipt_exists")
    receipt = seed_legacy(args.workspace_root, args.fixture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(receipt, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
