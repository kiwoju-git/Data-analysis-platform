from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite, sqrt
from pathlib import Path
from typing import Any, Final, Literal
from uuid import UUID, uuid4

from fastapi import status
from scipy import stats  # type: ignore[import-untyped]

from app.analyses.registry import get_method_version
from app.api.v1.schemas.analyses import (
    AnalysisProvenance,
    AnalysisResultEnvelope,
    AnalysisRunState,
    AnalysisWarning,
    RegressionPastedPredictionExecuteRequest,
    RegressionPastedPredictionMapping,
    RegressionPastedPredictionPreflightRequest,
    RegressionPastedPredictionPreflightResponse,
    RegressionPastedPredictionResponse,
    RegressionPastedPredictionRow,
    RegressionPastedPredictionRowsPageResponse,
    RegressionPredictionPreflightIssue,
    RegressionPredictionWarning,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import runtime_build_provenance
from app.services.regression_models import (
    _coefficient_estimates,
    _design_vector_for_manifest,
    _dot,
    _prediction_interval,
    _quadratic_form,
    _validated_prediction_basis,
    get_regression_model_manifest,
)
from app.storage.atomic import atomic_write_bytes
from app.storage.metadata import (
    AnalysisArtifactRecord,
    AnalysisRunRecord,
    get_analysis_run_record,
    insert_analysis_run_record_with_artifacts,
    list_analysis_artifact_records,
)

APP_VERSION = "0.1.0"
METHOD_ID: Final[Literal["regression.predict_pasted"]] = "regression.predict_pasted"
METHOD_VERSION = get_method_version(METHOD_ID)
MAX_ROWS = 10_000
MAX_CELL_LENGTH = 10_000
INLINE_ROWS = 1_000
INPUT_ARTIFACT_KIND = "regression_pasted_prediction_input"
ROWS_ARTIFACT_KIND = "regression_pasted_prediction_rows"


@dataclass(frozen=True)
class _PastedState:
    model_id: UUID
    manifest_sha256: str
    manifest: dict[str, Any]
    source_analysis_id: UUID
    source_dataset_version_id: UUID
    delimiter: Literal["tab", "comma"]
    has_header: bool
    rows: list[list[str]]
    mappings: list[RegressionPastedPredictionMapping]
    parsed_rows: list[tuple[int, dict[str, float | str]]]
    excluded_count: int
    issues: list[RegressionPredictionPreflightIssue]
    normalized_sha256: str


def preflight_regression_pasted_prediction(
    settings: Settings,
    *,
    model_id: UUID,
    body: RegressionPastedPredictionPreflightRequest,
) -> RegressionPastedPredictionPreflightResponse:
    return _preflight_response(_build_state(settings, model_id, body))


def create_regression_pasted_prediction(
    settings: Settings,
    *,
    model_id: UUID,
    body: RegressionPastedPredictionExecuteRequest,
) -> RegressionPastedPredictionResponse:
    state = _build_state(
        settings,
        model_id,
        RegressionPastedPredictionPreflightRequest.model_validate(
            body.model_dump(
                mode="json",
                include={
                    "content",
                    "has_header",
                    "delimiter",
                    "column_mappings",
                    "expected_model_manifest_sha256",
                },
            )
        ),
    )
    preflight = _preflight_response(state)
    if body.expected_normalized_input_sha256 != state.normalized_sha256:
        raise _error(
            "regression_pasted_prediction_input_changed",
            "사전점검 후 붙여넣기 입력 또는 mapping이 변경되었습니다. 다시 점검하세요.",
            status.HTTP_409_CONFLICT,
        )
    if not preflight.prediction_ready:
        raise _error(
            "regression_pasted_prediction_preflight_failed",
            "붙여넣기 예측 사전점검 오류를 해결하세요.",
            status.HTTP_409_CONFLICT,
        )
    basis = _validated_prediction_basis(state.manifest)
    coefficients = _coefficient_estimates(state.manifest)
    t_critical = float(
        stats.t.ppf(1.0 - ((1.0 - body.confidence_level) / 2.0), df=basis.df_residual)
    )
    if not isfinite(t_critical):
        raise _error(
            "regression_prediction_manifest_invalid", "예측 구간 계산 정보를 검증할 수 없습니다."
        )
    all_rows: list[RegressionPastedPredictionRow] = []
    for row_index, values in state.parsed_rows:
        vector = _design_vector_for_manifest(
            manifest=state.manifest,
            values_by_source_column_id=values,
        )
        predicted = _dot(vector, coefficients)
        leverage = max(0.0, _quadratic_form(vector, basis.xtx_inverse))
        mean_interval = None
        observation_interval = None
        if body.include_intervals:
            mean_interval = _prediction_interval(
                center=predicted,
                standard_error=sqrt(basis.sigma_squared * leverage),
                t_critical=t_critical,
                confidence_level=body.confidence_level,
            )
            observation_interval = _prediction_interval(
                center=predicted,
                standard_error=sqrt(basis.sigma_squared * (1.0 + leverage)),
                t_critical=t_critical,
                confidence_level=body.confidence_level,
            )
        warnings = _row_extrapolation_warnings(state.manifest, values)
        all_rows.append(
            RegressionPastedPredictionRow(
                row_index=row_index,
                predictor_values=values,
                predicted_mean=predicted,
                mean_confidence_interval=mean_interval,
                prediction_interval=observation_interval,
                warnings=warnings,
            )
        )
    prediction_id = uuid4()
    created_at = _utc_now()
    response = RegressionPastedPredictionResponse(
        prediction_id=prediction_id,
        input_kind="pasted_table",
        model_id=model_id,
        source_analysis_id=state.source_analysis_id,
        source_dataset_version_id=state.source_dataset_version_id,
        model_manifest_sha256=state.manifest_sha256,
        normalized_input_sha256=state.normalized_sha256,
        row_count_total=len(state.rows),
        row_count_predicted=len(all_rows),
        row_count_excluded=state.excluded_count,
        row_count_omitted=max(0, len(all_rows) - INLINE_ROWS),
        row_limit=INLINE_ROWS,
        truncated=len(all_rows) > INLINE_ROWS,
        confidence_level=body.confidence_level,
        warnings=_warnings(state, all_rows),
        mappings=state.mappings,
        rows=all_rows[:INLINE_ROWS],
        created_at=created_at,
    )
    _persist(settings, state, body, response, all_rows)
    return response


def get_regression_pasted_prediction_rows(
    settings: Settings,
    *,
    prediction_id: UUID,
    offset: int,
    limit: int,
) -> RegressionPastedPredictionRowsPageResponse:
    record = get_analysis_run_record(settings.workspace_root, str(prediction_id))
    if record is None or record.method_id != METHOD_ID:
        raise _error(
            "regression_pasted_prediction_not_found",
            "붙여넣기 예측 결과를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    artifacts = list_analysis_artifact_records(settings.workspace_root, str(prediction_id))
    artifact = next((item for item in artifacts if item.kind == ROWS_ARTIFACT_KIND), None)
    if artifact is None:
        raise _artifact_error()
    path = _safe_artifact_path(settings.workspace_root, artifact.path)
    try:
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != artifact.sha256:
            raise _artifact_error()
        payload = json.loads(content.decode("utf-8"))
        rows = [RegressionPastedPredictionRow.model_validate(item) for item in payload["rows"]]
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise _artifact_error() from exc
    page = rows[offset : offset + limit]
    model_id = UUID(str(payload["model_id"]))
    return RegressionPastedPredictionRowsPageResponse(
        prediction_id=prediction_id,
        model_id=model_id,
        offset=offset,
        limit=limit,
        total=len(rows),
        returned=len(page),
        has_previous=offset > 0,
        has_next=offset + len(page) < len(rows),
        rows=page,
    )


def _build_state(
    settings: Settings,
    model_id: UUID,
    body: RegressionPastedPredictionPreflightRequest,
) -> _PastedState:
    model = get_regression_model_manifest(settings, model_id)
    if model.manifest_sha256 != body.expected_model_manifest_sha256:
        raise _error(
            "regression_prediction_model_manifest_mismatch",
            "회귀모델 manifest가 사전 확인 시점과 다릅니다.",
            status.HTTP_409_CONFLICT,
        )
    source = get_analysis_run_record(settings.workspace_root, str(model.analysis_id))
    if source is None or source.stale:
        raise _error(
            "regression_prediction_source_model_stale",
            "현재 schema에 맞는 회귀모델을 다시 적합하세요.",
            status.HTTP_409_CONFLICT,
        )
    delimiter = _delimiter(body.content, body.delimiter)
    table = _parse_table(body.content, delimiter)
    if body.has_header and len(table) == 1:
        raise _error(
            "regression_pasted_prediction_header_without_data",
            "첫 행을 열 이름으로 사용하도록 설정되어 실제 예측 데이터 행이 없습니다. "
            "열 이름이 없는 값 한 행을 붙여넣었다면 첫 행에 열 이름 포함을 해제하세요.",
        )
    if len(table) < (2 if body.has_header else 1):
        raise _error("regression_pasted_prediction_no_rows", "예측할 행이 없습니다.")
    header = table[0] if body.has_header else [f"열 {index + 1}" for index in range(len(table[0]))]
    data_rows = table[1:] if body.has_header else table
    if len(data_rows) > MAX_ROWS:
        raise _error(
            "regression_pasted_prediction_row_limit", "붙여넣기 예측은 최대 10,000행입니다."
        )
    if len(set(header)) != len(header):
        raise _error("regression_pasted_prediction_duplicate_header", "중복된 header가 있습니다.")
    mappings = _resolve_mappings(model.manifest, header, body.column_mappings)
    domains = _domains(model.manifest)
    parsed_rows: list[tuple[int, dict[str, float | str]]] = []
    excluded = 0
    issues: list[RegressionPredictionPreflightIssue] = []
    error_counts: dict[str, int] = {}
    for row_index, row in enumerate(data_rows):
        values: dict[str, float | str] = {}
        valid = True
        for mapping in mappings:
            raw = (
                row[mapping.input_column_index].strip()
                if mapping.input_column_index < len(row)
                else ""
            )
            if raw == "":
                error_counts["regression_pasted_prediction_missing_value"] = (
                    error_counts.get("regression_pasted_prediction_missing_value", 0) + 1
                )
                valid = False
                continue
            domain = domains[mapping.source_column_id]
            if mapping.predictor_kind == "numeric":
                try:
                    value = float(raw)
                except ValueError:
                    error_counts["regression_pasted_prediction_non_numeric"] = (
                        error_counts.get("regression_pasted_prediction_non_numeric", 0) + 1
                    )
                    valid = False
                    continue
                if not isfinite(value):
                    valid = False
                    continue
                values[mapping.source_column_id] = value
            else:
                levels = domain.get("levels")
                if not isinstance(levels, list) or raw not in levels:
                    error_counts["regression_pasted_prediction_unseen_level"] = (
                        error_counts.get("regression_pasted_prediction_unseen_level", 0) + 1
                    )
                    valid = False
                    continue
                values[mapping.source_column_id] = raw
        if valid:
            parsed_rows.append((row_index, values))
        else:
            excluded += 1
    messages = {
        "regression_pasted_prediction_missing_value": (
            "필수 predictor 값이 비어 있는 행이 있습니다."
        ),
        "regression_pasted_prediction_non_numeric": (
            "숫자형 predictor로 해석할 수 없는 값이 있습니다."
        ),
        "regression_pasted_prediction_unseen_level": "학습에 없던 범주 수준이 있습니다.",
    }
    for code, count in sorted(error_counts.items()):
        issues.append(
            RegressionPredictionPreflightIssue(
                code=code,
                severity="warning",
                message=messages[code],
                count=count,
            )
        )
    if not parsed_rows:
        issues.append(
            RegressionPredictionPreflightIssue(
                code="regression_pasted_prediction_no_usable_rows",
                severity="error",
                message="예측 가능한 행이 없습니다.",
                count=0,
            )
        )
    normalized_payload = {
        "input_schema_version": 1,
        "model_id": str(model_id),
        "model_manifest_sha256": model.manifest_sha256,
        "delimiter": delimiter,
        "has_header": body.has_header,
        "header": header,
        "rows": data_rows,
        "mappings": [mapping.model_dump(mode="json") for mapping in mappings],
    }
    return _PastedState(
        model_id=model_id,
        manifest_sha256=model.manifest_sha256,
        manifest=model.manifest,
        source_analysis_id=model.analysis_id,
        source_dataset_version_id=model.dataset_version_id,
        delimiter=delimiter,
        has_header=body.has_header,
        rows=data_rows,
        mappings=mappings,
        parsed_rows=parsed_rows,
        excluded_count=excluded,
        issues=issues,
        normalized_sha256=hashlib.sha256(_canonical_bytes(normalized_payload)).hexdigest(),
    )


def _preflight_response(state: _PastedState) -> RegressionPastedPredictionPreflightResponse:
    return RegressionPastedPredictionPreflightResponse(
        input_schema_version=1,
        model_id=state.model_id,
        model_manifest_sha256=state.manifest_sha256,
        normalized_input_sha256=state.normalized_sha256,
        delimiter=state.delimiter,
        has_header=state.has_header,
        row_count_total=len(state.rows),
        row_count_usable=len(state.parsed_rows),
        row_count_excluded=state.excluded_count,
        prediction_ready=bool(state.parsed_rows)
        and not any(issue.severity == "error" for issue in state.issues),
        mappings=state.mappings,
        preview_rows=state.rows[:10],
        issues=state.issues,
    )


def _parse_table(content: str, delimiter: Literal["tab", "comma"]) -> list[list[str]]:
    character = "\t" if delimiter == "tab" else ","
    try:
        rows = [
            [cell.strip() for cell in row]
            for row in csv.reader(
                io.StringIO(content.replace("\r\n", "\n").replace("\r", "\n")), delimiter=character
            )
            if any(cell.strip() for cell in row)
        ]
    except csv.Error as exc:
        raise _error(
            "regression_pasted_prediction_parse_failed", "붙여넣기 표를 해석할 수 없습니다."
        ) from exc
    if any(len(cell) > MAX_CELL_LENGTH for row in rows for cell in row):
        raise _error(
            "regression_pasted_prediction_cell_too_long",
            "붙여넣기 cell 길이가 허용 범위를 초과했습니다.",
        )
    return rows


def _delimiter(content: str, requested: str) -> Literal["tab", "comma"]:
    if requested == "tab":
        return "tab"
    if requested == "comma":
        return "comma"
    first_line = content.splitlines()[0] if content.splitlines() else ""
    return "tab" if first_line.count("\t") >= first_line.count(",") else "comma"


def _resolve_mappings(
    manifest: dict[str, Any],
    header: list[str],
    requested: list[Any],
) -> list[RegressionPastedPredictionMapping]:
    predictors = manifest.get("predictors")
    domains = _domains(manifest)
    if not isinstance(predictors, list) or not predictors:
        raise _error(
            "regression_prediction_manifest_invalid",
            "회귀모델 predictor 정보를 검증할 수 없습니다.",
        )
    requested_by_source = {item.source_column_id: item.input_column_index for item in requested}
    if len(requested_by_source) != len(requested):
        raise _error(
            "regression_pasted_prediction_mapping_duplicate", "predictor mapping이 중복되었습니다."
        )
    mappings: list[RegressionPastedPredictionMapping] = []
    for predictor in predictors:
        if not isinstance(predictor, dict):
            raise _error(
                "regression_prediction_manifest_invalid",
                "회귀모델 predictor 정보를 검증할 수 없습니다.",
            )
        column_id = str(predictor.get("column_id"))
        display_name = str(predictor.get("display_name", column_id))
        index = requested_by_source.get(column_id)
        if index is None:
            matches = [
                position
                for position, name in enumerate(header)
                if name in {column_id, display_name}
            ]
            if len(matches) == 1:
                index = matches[0]
            elif len(predictors) == 1 and len(header) == 1:
                index = 0
            else:
                raise _error(
                    "regression_pasted_prediction_mapping_required",
                    f"{display_name} predictor mapping을 지정하세요.",
                )
        if index >= len(header):
            raise _error(
                "regression_pasted_prediction_mapping_invalid",
                "predictor mapping column index가 올바르지 않습니다.",
            )
        kind = domains[column_id].get("kind")
        if kind not in {"numeric", "categorical"}:
            raise _error(
                "regression_prediction_manifest_invalid",
                "회귀모델 predictor 종류를 검증할 수 없습니다.",
            )
        mappings.append(
            RegressionPastedPredictionMapping(
                input_column_index=index,
                input_column_name=header[index],
                source_column_id=column_id,
                display_name=display_name,
                predictor_kind=kind,
            )
        )
    if len({mapping.input_column_index for mapping in mappings}) != len(mappings):
        raise _error(
            "regression_pasted_prediction_mapping_duplicate",
            "하나의 입력 column을 여러 predictor에 mapping할 수 없습니다.",
        )
    return mappings


def _domains(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    training = manifest.get("training_domain")
    predictors = training.get("predictors") if isinstance(training, dict) else None
    if not isinstance(predictors, list):
        raise _error(
            "regression_prediction_manifest_invalid", "회귀모델 학습 범위를 검증할 수 없습니다."
        )
    return {
        str(item["column_id"]): item
        for item in predictors
        if isinstance(item, dict) and "column_id" in item
    }


def _row_extrapolation_warnings(
    manifest: dict[str, Any], values: dict[str, float | str]
) -> list[str]:
    warnings: list[str] = []
    for column_id, domain in _domains(manifest).items():
        value = values.get(column_id)
        if domain.get("kind") == "numeric" and isinstance(value, float):
            if value < float(domain["minimum"]) or value > float(domain["maximum"]):
                warnings.append("prediction_extrapolation_risk")
    return warnings


def _warnings(
    state: _PastedState, rows: list[RegressionPastedPredictionRow]
) -> list[RegressionPredictionWarning]:
    warnings = [
        RegressionPredictionWarning(
            code="regression_prediction_not_causation",
            severity="info",
            message="회귀 예측은 관찰 데이터 기반 수학적 예측이며 인과 효과를 의미하지 않습니다.",
        )
    ]
    if state.excluded_count:
        warnings.append(
            RegressionPredictionWarning(
                code="regression_pasted_prediction_rows_excluded",
                severity="warning",
                message="결측, 숫자 해석 오류 또는 unseen 수준이 있는 행을 제외했습니다.",
                count=state.excluded_count,
            )
        )
    extrapolated = sum("prediction_extrapolation_risk" in row.warnings for row in rows)
    if extrapolated:
        warnings.append(
            RegressionPredictionWarning(
                code="prediction_extrapolation_risk",
                severity="warning",
                message="일부 입력이 회귀 학습 범위를 벗어났습니다.",
                count=extrapolated,
            )
        )
    return warnings


def _persist(
    settings: Settings,
    state: _PastedState,
    request: RegressionPastedPredictionExecuteRequest,
    response: RegressionPastedPredictionResponse,
    all_rows: list[RegressionPastedPredictionRow],
) -> None:
    input_payload = {
        "artifact_schema_version": 1,
        "artifact_kind": INPUT_ARTIFACT_KIND,
        "prediction_id": str(response.prediction_id),
        "model_id": str(response.model_id),
        "model_manifest_sha256": response.model_manifest_sha256,
        "normalized_input_sha256": response.normalized_input_sha256,
        "delimiter": state.delimiter,
        "has_header": state.has_header,
        "mappings": [item.model_dump(mode="json") for item in state.mappings],
        "rows": state.rows,
    }
    rows_payload = {
        "artifact_schema_version": 1,
        "artifact_kind": ROWS_ARTIFACT_KIND,
        "prediction_id": str(response.prediction_id),
        "model_id": str(response.model_id),
        "rows": [item.model_dump(mode="json") for item in all_rows],
    }
    envelope = AnalysisResultEnvelope(
        analysis_id=response.prediction_id,
        method_id=METHOD_ID,
        method_version=METHOD_VERSION,
        dataset_version_id=response.source_dataset_version_id,
        status="succeeded",
        warnings=[
            AnalysisWarning(code=item.code, severity=item.severity, message=item.message)
            for item in response.warnings
        ],
        provenance=AnalysisProvenance(
            method_id=METHOD_ID,
            method_version=METHOD_VERSION,
            dataset_version_id=response.source_dataset_version_id,
            app_version=APP_VERSION,
            **runtime_build_provenance(settings),
        ),
        result=response.model_dump(mode="json"),
    )
    result_path = _relative_path(response.prediction_id, "result.json")
    input_path = _relative_path(response.prediction_id, "pasted_input.json")
    rows_path = _relative_path(response.prediction_id, "prediction_rows.json")
    result_bytes = _canonical_bytes(envelope.model_dump(mode="json"))
    input_bytes = _canonical_bytes(input_payload)
    rows_bytes = _canonical_bytes(rows_payload)
    try:
        atomic_write_bytes(settings.workspace_root / result_path, result_bytes)
        atomic_write_bytes(settings.workspace_root / input_path, input_bytes)
        atomic_write_bytes(settings.workspace_root / rows_path, rows_bytes)
        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(response.prediction_id),
                method_id=METHOD_ID,
                method_version=METHOD_VERSION,
                dataset_version_id=str(response.source_dataset_version_id),
                config_json=_canonical_bytes(
                    {
                        "config_schema_version": 1,
                        "input_kind": "pasted_table",
                        "model_id": str(response.model_id),
                        "model_manifest_sha256": response.model_manifest_sha256,
                        "normalized_input_sha256": response.normalized_input_sha256,
                        "confidence_level": request.confidence_level,
                        "include_intervals": request.include_intervals,
                    }
                ).decode("utf-8"),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_path.as_posix(),
                result_sha256=hashlib.sha256(result_bytes).hexdigest(),
                stale=False,
                created_at=response.created_at,
                updated_at=response.created_at,
                completed_at=response.created_at,
                app_version=APP_VERSION,
            ),
            [
                AnalysisArtifactRecord(
                    str(uuid4()),
                    str(response.prediction_id),
                    INPUT_ARTIFACT_KIND,
                    input_path.as_posix(),
                    hashlib.sha256(input_bytes).hexdigest(),
                    "application/json",
                    response.created_at,
                ),
                AnalysisArtifactRecord(
                    str(uuid4()),
                    str(response.prediction_id),
                    ROWS_ARTIFACT_KIND,
                    rows_path.as_posix(),
                    hashlib.sha256(rows_bytes).hexdigest(),
                    "application/json",
                    response.created_at,
                ),
            ],
        )
    except Exception:
        for path in (result_path, input_path, rows_path):
            try:
                (settings.workspace_root / path).unlink()
            except FileNotFoundError:
                pass
        raise


def _safe_artifact_path(workspace_root: Path, stored_path: str) -> Path:
    relative = Path(stored_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise _artifact_error()
    return workspace_root / relative


def _artifact_error() -> ApiError:
    return _error(
        "regression_pasted_prediction_artifact_invalid",
        "붙여넣기 예측 행 artifact를 검증할 수 없습니다.",
        status.HTTP_409_CONFLICT,
    )


def _error(
    code: str, message: str, status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
) -> ApiError:
    return ApiError(code=code, message=message, status_code=status_code)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _relative_path(prediction_id: UUID, filename: str) -> Path:
    return Path("workspaces") / "analyses" / str(prediction_id) / filename


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
