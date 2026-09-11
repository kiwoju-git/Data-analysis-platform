from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Any
from uuid import UUID, uuid4

import numpy as np
from pydantic import ValidationError
from scipy import stats  # type: ignore[import-untyped]

from app.api.v1.schemas.doe import (
    DoeFactorialAnalysisResponse,
    FactorialDesignResponse,
    GeneralFactorialAnalysisResponse,
    GeneralFactorialDesignResponse,
)
from app.api.v1.schemas.doe_model_workflow import (
    DoeFinalModelWorkflow,
    DoePredictedRow,
    DoePredictionCreateRequest,
    DoePredictionInterval,
    DoePredictionPreflightRequest,
    DoePredictionPreflightResponse,
    DoePredictionResponse,
    DoePredictionRowIssue,
    DoePredictionRowRequest,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import utc_now
from app.services.doe_designs import get_factorial_design
from app.services.doe_factorial_analysis import get_factorial_analysis
from app.services.general_factorial_designs import (
    get_general_factorial_analysis,
    get_general_factorial_design,
)
from app.statistics.doe_factor_domain import DoeFactorDomain
from app.statistics.factorial_model_workflow import FactorialFeature, feature_row
from app.storage.factorial_analysis_assets import FactorialAnalysisAsset, get_asset, insert_asset
from app.storage.metadata import (
    WorkspaceAssetStorageConflict,
    get_experiment_design_analysis_record,
    get_experiment_design_record,
)


@dataclass(frozen=True)
class FactorialModelSource:
    design: FactorialDesignResponse | GeneralFactorialDesignResponse
    analysis: DoeFactorialAnalysisResponse | GeneralFactorialAnalysisResponse
    result: dict[str, Any]
    sha256: str
    final_model: DoeFinalModelWorkflow | None


def workflow_error(code: str, status_code: int = 409) -> ApiError:
    return ApiError(
        code=code,
        message="The factorial analysis workflow could not complete this operation.",
        status_code=status_code,
    )


def load_factorial_model_source(
    settings: Settings, design_id: UUID, analysis_id: UUID, *, require_model: bool = True
) -> FactorialModelSource:
    design_record = get_experiment_design_record(settings.workspace_root, str(design_id))
    if design_record is None:
        raise workflow_error("doe_design_not_found", 404)
    design: FactorialDesignResponse | GeneralFactorialDesignResponse
    analysis: DoeFactorialAnalysisResponse | GeneralFactorialAnalysisResponse
    result: dict[str, Any]
    if design_record.method_id == "doe.general_factorial_design":
        design = get_general_factorial_design(settings, design_id)
        analysis = get_general_factorial_analysis(settings, design_id, analysis_id)
        result = analysis.result
    elif design_record.method_id == "doe.factorial_design":
        design = get_factorial_design(settings, design_id)
        analysis = get_factorial_analysis(settings, design_id, analysis_id)
        result = analysis.result.model_dump(mode="json")
    else:
        raise workflow_error("doe_factorial_prediction_design_unsupported")
    record = get_experiment_design_analysis_record(settings.workspace_root, str(analysis_id))
    if (
        record is None
        or hashlib.sha256(record.result_json.encode("utf-8")).hexdigest() != record.result_sha256
    ):
        raise workflow_error("doe_factorial_analysis_checksum_mismatch")
    final_model = None
    if result.get("final_model") is not None:
        try:
            final_model = DoeFinalModelWorkflow.model_validate(result["final_model"])
        except ValidationError as exc:
            raise workflow_error("doe_factorial_prediction_basis_invalid") from exc
        basis = final_model.prediction_basis
        p = len(basis.features)
        if (
            p < 1
            or p > 256
            or len(basis.coefficients) != p
            or len(basis.xtx_inverse) != p
            or any(len(row) != p for row in basis.xtx_inverse)
            or basis.features[0].kind != "intercept"
            or sum(feature.kind == "intercept" for feature in basis.features) != 1
            or basis.residual_df != result["sample"]["n_observations"] - p
            or basis.residual_df < 0
            or not 0 < basis.confidence_level < 1
            or not basis.block_levels
            or (basis.residual_mean_square is not None and basis.residual_mean_square < 0)
            or any(
                not set(feature.factor_names).issubset({factor.name for factor in design.factors})
                for feature in basis.features
            )
            or len(final_model.coded_coefficients) != p
            or basis.coefficients != [row.coefficient for row in final_model.coded_coefficients]
            or set(feature.term_id for feature in basis.features)
            != set(
                result["model_selection"]["final_term_ids"]
                + result["model_selection"]["fixed_term_ids"]
            )
        ):
            raise workflow_error("doe_factorial_prediction_basis_invalid")
        inverse = np.asarray(basis.xtx_inverse, dtype=float)
        if not np.allclose(inverse, inverse.T, rtol=1e-10, atol=1e-12):
            raise workflow_error("doe_factorial_prediction_basis_invalid")
        try:
            np.linalg.cholesky(inverse)
        except np.linalg.LinAlgError as exc:
            raise workflow_error("doe_factorial_prediction_basis_invalid") from exc
    if require_model and final_model is None:
        raise workflow_error("doe_factorial_prediction_legacy_basis_unavailable")
    if (
        require_model
        and isinstance(design, FactorialDesignResponse)
        and (design.fractional is not None or design.screening is not None)
    ):
        raise workflow_error("doe_factorial_prediction_design_unsupported")
    return FactorialModelSource(design, analysis, result, record.result_sha256, final_model)


def factorial_prediction_preflight(
    settings: Settings, design_id: UUID, analysis_id: UUID, body: DoePredictionPreflightRequest
) -> DoePredictionPreflightResponse:
    source = load_factorial_model_source(settings, design_id, analysis_id)
    return _preflight(source, body)


def _preflight(
    source: FactorialModelSource, body: DoePredictionPreflightRequest
) -> DoePredictionPreflightResponse:
    issues: list[DoePredictionRowIssue] = []
    seen: set[str] = set()
    for row in body.rows:
        if row.row_id in seen:
            issues.append(
                DoePredictionRowIssue(
                    row_id=row.row_id, code="doe_factorial_prediction_duplicate_row"
                )
            )
        seen.add(row.row_id)
        _, _, row_issues = _row_settings(source, row)
        issues.extend(row_issues)
    payload = {
        "source_sha256": source.sha256,
        "request": body.model_dump(mode="json", exclude={"expected_preflight_sha256"}),
    }
    return DoePredictionPreflightResponse(
        design_id=source.design.design_id,
        analysis_id=source.analysis.analysis_id,
        source_analysis_sha256=source.sha256,
        preflight_sha256=hashlib.sha256(_json_bytes(payload)).hexdigest(),
        valid=not issues,
        row_count=len(body.rows),
        issues=issues,
        warnings=["doe_factorial_post_selection_inference_exploratory"]
        if source.result.get("model_selection", {}).get("method") == "backward_elimination"
        else [],
    )


def _row_settings(
    source: FactorialModelSource, row: DoePredictionRowRequest
) -> tuple[dict[str, float], bool, list[DoePredictionRowIssue]]:
    assert source.final_model is not None
    basis = source.final_model.prediction_basis
    errors: list[DoePredictionRowIssue] = []
    settings: dict[str, float] = {}

    def issue(code: str, name: str | None = None) -> None:
        errors.append(DoePredictionRowIssue(row_id=row.row_id, code=code, factor_name=name))

    if set(row.factor_settings) != {factor.name for factor in source.design.factors}:
        issue("doe_factorial_prediction_factor_set_invalid")
        return settings, False, errors
    if row.block_index is not None and row.block_index not in basis.block_levels:
        issue("doe_factorial_prediction_block_invalid")
    if isinstance(source.design, GeneralFactorialDesignResponse):
        for general_factor in source.design.factors:
            value = row.factor_settings[general_factor.name]
            matches = [
                index
                for index, level in enumerate(general_factor.levels)
                if value == level and isinstance(value, str) == isinstance(level, str)
            ]
            if not matches:
                issue("doe_factorial_prediction_unknown_level", general_factor.name)
            else:
                settings[general_factor.name] = float(matches[0])
        return settings, False, errors
    for factor in source.design.factors:
        value = row.factor_settings[factor.name]
        if factor.factor_kind == "categorical":
            if value not in (factor.low_label, factor.high_label):
                issue("doe_factorial_prediction_unknown_level", factor.name)
            else:
                settings[factor.name] = -1.0 if value == factor.low_label else 1.0
        elif isinstance(value, str) or not isfinite(value):
            issue("doe_factorial_prediction_numeric_required", factor.name)
        else:
            domain = DoeFactorDomain(
                factor.low, factor.high, factor.domain_kind, factor.step, factor.display_decimals
            )
            if not domain.is_executable(value):
                issue("doe_factorial_prediction_outside_domain", factor.name)
            settings[factor.name] = 2 * (value - factor.low) / (factor.high - factor.low) - 1
    center = any(
        all(
            name in settings and abs(settings[name] - value) <= 1e-12
            for name, value in candidate.items()
        )
        for candidate in basis.center_settings
    )
    if not errors and any(feature.kind == "center_curvature" for feature in basis.features):
        corner = all(abs(abs(value) - 1) <= 1e-12 for value in settings.values())
        if not corner and not center:
            issue("doe_factorial_prediction_center_curvature_domain_invalid")
    return settings, center, errors


def create_factorial_prediction(
    settings: Settings, design_id: UUID, analysis_id: UUID, body: DoePredictionCreateRequest
) -> DoePredictionResponse:
    source = load_factorial_model_source(settings, design_id, analysis_id)
    preflight = _preflight(source, body)
    if not preflight.valid:
        raise workflow_error("doe_factorial_prediction_input_invalid")
    if body.expected_preflight_sha256 != preflight.preflight_sha256:
        raise workflow_error("doe_factorial_prediction_preflight_stale")
    assert source.final_model is not None
    basis = source.final_model.prediction_basis
    features = [
        FactorialFeature(
            item.term_id,
            item.label,
            item.kind,
            tuple(item.factor_names),
            tuple(item.level_indices),
            item.block_index,
        )
        for item in basis.features
    ]
    inverse = np.asarray(basis.xtx_inverse, dtype=float)
    coefficients = np.asarray(basis.coefficients, dtype=float)
    mse = basis.residual_mean_square
    available = mse is not None and mse > 0 and basis.residual_df > 0
    critical = (
        float(stats.t.ppf(0.5 + body.confidence_level / 2, basis.residual_df))
        if available
        else None
    )
    predictions = []
    for row in body.rows:
        values, center, _ = _row_settings(source, row)
        block = row.block_index if row.block_index is not None else basis.block_levels[0]
        vector = np.asarray(feature_row(features, values, center_point=center, block_index=block))
        mean = float(vector @ coefficients)
        leverage = float(vector @ inverse @ vector)
        if not isfinite(mean) or not isfinite(leverage) or leverage < -1e-10:
            raise workflow_error("doe_factorial_prediction_basis_invalid")
        se = sqrt(mse * max(0.0, leverage)) if available and mse is not None else None
        pi_se = sqrt(mse * (1 + max(0.0, leverage))) if available and mse is not None else None
        mean_ci = (
            DoePredictionInterval(
                lower=mean - critical * se, upper=mean + critical * se, level=body.confidence_level
            )
            if critical is not None and se is not None
            else None
        )
        pi = (
            DoePredictionInterval(
                lower=mean - critical * pi_se,
                upper=mean + critical * pi_se,
                level=body.confidence_level,
            )
            if critical is not None and pi_se is not None
            else None
        )
        predictions.append(
            DoePredictedRow(
                row_id=row.row_id,
                factor_settings=row.factor_settings,
                block_index=block,
                fitted_mean=mean,
                standard_error_fit=se,
                mean_confidence_interval=mean_ci,
                individual_prediction_interval=pi,
                interval_unavailability_reason=None
                if available
                else "doe_factorial_prediction_variance_unavailable",
            )
        )
    result = DoePredictionResponse(
        prediction_id=uuid4(),
        design_id=design_id,
        analysis_id=analysis_id,
        response_revision_id=source.analysis.response_revision_id,
        response_revision_sha256=source.analysis.response_revision_sha256,
        source_analysis_sha256=source.sha256,
        created_at=utc_now(),
        rows=predictions,
        warnings=preflight.warnings,
    )
    content = _json_bytes(result.model_dump(mode="json"))
    try:
        insert_asset(
            settings.workspace_root,
            FactorialAnalysisAsset(
                str(result.prediction_id),
                str(analysis_id),
                "prediction",
                1,
                None,
                source.sha256,
                hashlib.sha256(content).hexdigest(),
                "application/json",
                len(content),
                result.created_at,
            ),
            content,
        )
    except WorkspaceAssetStorageConflict as exc:
        raise workflow_error(exc.code) from exc
    return result


def get_factorial_prediction(
    settings: Settings, design_id: UUID, analysis_id: UUID, prediction_id: UUID
) -> DoePredictionResponse:
    source = load_factorial_model_source(settings, design_id, analysis_id)
    try:
        stored = get_asset(settings.workspace_root, str(analysis_id), str(prediction_id))
        if stored is None or stored[0].kind != "prediction":
            raise workflow_error("doe_factorial_prediction_not_found", 404)
        record, content = stored
        result = DoePredictionResponse.model_validate_json(content)
        if (
            record.source_analysis_sha256 != source.sha256
            or result.source_analysis_sha256 != source.sha256
            or result.analysis_id != analysis_id
            or result.prediction_id != prediction_id
        ):
            raise workflow_error("doe_factorial_prediction_source_changed")
        return result
    except WorkspaceAssetStorageConflict as exc:
        raise workflow_error(exc.code) from exc
    except ValidationError as exc:
        raise workflow_error("doe_factorial_prediction_metadata_invalid") from exc


def _json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
