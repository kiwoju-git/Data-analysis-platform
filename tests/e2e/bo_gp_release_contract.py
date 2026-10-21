"""Pure identity contract shared by exact-archive journeys and their verifier."""

from __future__ import annotations

import hashlib
import json
import re
from uuid import UUID


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def _uuid(value: object) -> bool:
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except ValueError:
        return False


def _hash(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError("BO/GPR archive owner/source identity is incomplete")


def report_identity(kind: str, saved: dict) -> list[dict]:
    _require(isinstance(saved, dict) and _hash(saved.get("source_ref_sha256")))
    _require(
        isinstance(saved.get("snapshot"), dict)
        and isinstance(saved["snapshot"].get("payload"), dict)
    )
    _require(isinstance(saved.get("source"), dict))
    actual_ref = hashlib.sha256(
        json.dumps(
            saved["source"], sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    _require(actual_ref == saved["source_ref_sha256"])
    artifacts = saved.get("reports")
    _require(isinstance(artifacts, list) and bool(artifacts))
    identities = []
    for artifact in artifacts:
        descriptor = artifact.get("descriptor", {})
        _require(_uuid(descriptor.get("export_id")) and _hash(descriptor.get("sha256")))
        _require(
            descriptor.get("locale") in {"en", "ko"}
            and descriptor.get("source") == saved["source"]
        )
        _require(isinstance(artifact.get("path"), str) and bool(artifact["path"]))
        identities.append(
            {
                "kind": kind,
                "export_id": descriptor["export_id"],
                "locale": descriptor["locale"],
                "source_ref_sha256": actual_ref,
                "output_sha256": descriptor["sha256"],
                "snapshot_sha256": digest(saved["snapshot"]["payload"]),
            }
        )
    _require(len({item["export_id"] for item in identities}) == len(identities))
    return identities


def bo_identity(receipt: dict) -> dict:
    uuid_fields = (
        "study_id",
        "batch_id",
        "current_history_revision_id",
        "source_history_revision_id",
        "replicate_parent_trial_id",
    )
    hash_fields = (
        "stored_batch_sha256",
        "study_payload_sha256",
        "current_history_sha256",
        "source_history_sha256",
    )
    _require(isinstance(receipt, dict))
    _require(all(_uuid(receipt.get(key)) for key in uuid_fields))
    _require(all(_hash(receipt.get(key)) for key in hash_fields))
    replicates = receipt.get("replicate_trial_ids")
    _require(
        isinstance(replicates, list)
        and len(replicates) == 2
        and all(_uuid(item) for item in replicates)
    )
    _require(
        len(set(replicates)) == 2
        and receipt["replicate_parent_trial_id"] not in replicates
    )
    source = receipt.get("managed_report", {}).get("source", {})
    _require(
        source.get("study_id") == receipt["study_id"]
        and source.get("history_revision_id") == receipt["source_history_revision_id"]
    )
    _require(source.get("expected_source_sha256") == receipt["source_history_sha256"])
    _require(source.get("attachment", {}).get("batch_id") == receipt["batch_id"])
    return {
        **{key: receipt[key] for key in (*uuid_fields, *hash_fields)},
        "replicate_trial_ids": replicates,
    }


def gp_identity(receipt: dict) -> dict:
    _require(isinstance(receipt, dict) and _uuid(receipt.get("version_id")))
    analyses = receipt.get("analyses")
    _require(isinstance(analyses, list) and len(analyses) == 3)
    owners = []
    for index, envelope in enumerate(analyses):
        _require(isinstance(envelope, dict) and _uuid(envelope.get("analysis_id")))
        result = envelope.get("result", {})
        pointer = result.get("model_manifest", {})
        _require(
            result.get("schema_version") == 4
            and _uuid(pointer.get("model_id"))
            and _hash(pointer.get("manifest_sha256"))
        )
        _require(
            result.get("validation_plan", {}).get("effective_method")
            == ("group_k_fold" if index == 0 else "time_series_split")
        )
        _require(bool(result.get("feature_lineage")) is (index == 2))
        owners.append(
            {
                "analysis_id": envelope["analysis_id"],
                "model_id": pointer["model_id"],
                "manifest_sha256": pointer["manifest_sha256"],
                "result_payload_sha256": digest(result),
            }
        )
    _require(len({item["analysis_id"] for item in owners}) == 3)
    predictions = []
    for kind, response_key, request_key, owner in (
        ("mixed", "prediction", "prediction_request", owners[0]),
        ("lag", "lag_prediction", "lag_prediction_request", owners[2]),
        ("surface", "surface_prediction", "surface_request", owners[0]),
    ):
        response, request = receipt.get(response_key), receipt.get(request_key)
        _require(isinstance(response, dict) and isinstance(request, dict))
        _require(
            response.get("model_id") == owner["model_id"]
            and request.get("expected_model_manifest_sha256")
            == owner["manifest_sha256"]
        )
        rows = response.get("rows")
        _require(
            isinstance(rows, list)
            and bool(rows)
            and isinstance(request.get("rows"), list)
        )
        _require(
            {row.get("client_row_id") for row in rows}
            == {row.get("client_row_id") for row in request["rows"]}
        )
        _require(
            len({row.get("client_row_id") for row in rows})
            == len(rows)
            == len(request["rows"])
        )
        if kind == "surface":
            view = request.get("surface_view", {})
            _require(
                view.get("display_mode") == "latent_sd"
                and isinstance(view.get("hold_values"), dict)
                and bool(view["hold_values"])
            )
            _require(
                type(view.get("grid_size")) is int
                and len(rows) == view["grid_size"] ** 2
            )
        if kind in {"mixed", "surface"}:
            managed = receipt.get(
                "managed" if kind == "mixed" else "surface_managed", {}
            )
            payload = managed.get("snapshot", {}).get("payload", {})
            _require(
                payload.get("request") == request
                and payload.get("result", {}).get("rows") == rows
            )
            _require(
                payload.get("model_id") == owner["model_id"]
                and payload.get("model_manifest_sha256") == owner["manifest_sha256"]
            )
        predictions.append(
            {
                "kind": kind,
                "model_id": owner["model_id"],
                "manifest_sha256": owner["manifest_sha256"],
                "request_sha256": digest(request),
                "rows_sha256": digest(rows),
            }
        )
    return {
        "version_id": receipt["version_id"],
        "analyses": owners,
        "predictions": predictions,
    }


def extension_identity(original: dict) -> dict:
    bo, gp = original["bo_noise_receipt"], original["gp_extension_receipt"]
    reports = []
    for kind, saved in (
        ("bo", bo.get("managed_report")),
        ("mixed", gp.get("managed")),
        ("surface", gp.get("surface_managed")),
    ):
        reports.extend(report_identity(kind, saved))
    return {"bo": bo_identity(bo), "gp": gp_identity(gp), "reports": reports}


def require_phase(receipt: object, phase: str) -> None:
    _require(isinstance(receipt, dict))
    _require(
        type(receipt.get("schema_version")) is int
        and receipt.get("schema_version") == 1
        and receipt.get("phase") == phase
        and receipt.get("status") == "succeeded"
    )
    _require(receipt.get("forbidden_mutation_requests") == [])
    identity = receipt.get("identity")
    _require(
        isinstance(identity, dict)
        and isinstance(identity.get("reports"), list)
        and bool(identity["reports"])
    )
    _require(receipt.get("identity_sha256") == digest(identity))
    if phase == "resume":
        _require(
            isinstance(identity.get("bo"), dict)
            and isinstance(identity.get("gp"), dict)
        )
        _require(
            receipt.get("models_predicted_without_save") is True
            and receipt.get("exact_sources_visible") is True
        )
    else:
        _require(
            phase == "offline"
            and receipt.get("stored_surface_geometry_visible") is True
        )


def require_roundtrip(original: dict, restarts: list[dict], offline: dict) -> dict:
    expected = extension_identity(original)
    _require(len(restarts) == 2)
    for restart in restarts:
        receipt = restart.get("bo_gp_receipt")
        require_phase(receipt, "resume")
        _require(receipt["identity"] == expected)
    receipt = offline.get("bo_gp_receipt")
    require_phase(receipt, "offline")
    _require(receipt["identity"] == {"reports": expected["reports"]})
    return {
        "schema_version": 1,
        "status": "succeeded",
        "identity_sha256": digest(expected),
        "same_install_restart": True,
        "second_install_shared_workspace": True,
        "server_stopped_reports": True,
    }
