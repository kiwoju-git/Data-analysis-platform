"""Evaluate once, save the exact server receipt, and restore without fitting."""

from time import monotonic
from typing import Any
from uuid import UUID, uuid4

from app.api.v1.schemas import bo_views as dto
from app.api.v1.schemas.bayesian import BayesianLinearConstraintRequest
from app.api.v1.schemas.bo_loo import LooRequest
from app.api.v1.schemas.bo_mixed_planning import EvaluatedMixedCandidateRow
from app.api.v1.schemas.bo_planning import EvaluatedCandidateRow
from app.core.config import Settings
from app.services import bo_planning
from app.services.analysis_run_execution import utc_now
from app.services.bo_view_receipts import BoViewReceiptStore, view_error
from app.statistics.doe_factor_domain import DoeFactorDomain
from app.storage import bo_views as storage
from app.storage.bayesian_studies import BayesianStorageConflict
from app.storage.bo_planning import planning_json, planning_sha


def _source(study_id: UUID, record: dict[str, Any]) -> dto.ViewSource:
    return dto.ViewSource(
        study_id=study_id,
        study_version_id=record["study_version_id"],
        definition_sha256=record["definition_sha256"],
        model_id=record["model_id"],
        model_sha256=record["snapshot_sha256"],
        model_config_sha256=record["config_sha256"],
        history_revision_id=record["source_history_revision_id"],
        history_sha256=record["history_sha256"],
    )


def _axis_values(factor: Any, count: int) -> tuple[list[float | str], int | None]:
    if factor.domain_kind in {"nominal", "ordinal"}:
        return list(factor.levels), len(factor.levels)
    domain = DoeFactorDomain(
        factor.low, factor.high, factor.domain_kind, factor.step, factor.display_decimals
    )
    if domain.domain_kind == "discrete_numeric":
        levels = domain.levels()
        indices = sorted(
            {
                round(i * (len(levels) - 1) / (min(count, len(levels)) - 1))
                for i in range(min(count, len(levels)))
            }
        )
        return [levels[index] for index in indices], len(levels)
    values = [
        factor.low,
        *(factor.low + (factor.high - factor.low) * i / (count - 1) for i in range(1, count - 1)),
        factor.high,
    ]
    return sorted(set(values)), None


def _validate_holds(factors: list[Any], holds: dict[str, float | str]) -> None:
    if set(holds) != {factor.factor_id for factor in factors}:
        raise view_error("bayesian_view_holds_invalid", 422)
    for factor in factors:
        value = holds[factor.factor_id]
        if factor.domain_kind in {"nominal", "ordinal"}:
            valid = isinstance(value, str) and value in factor.levels
        else:
            domain = DoeFactorDomain(
                factor.low, factor.high, factor.domain_kind, factor.step, factor.display_decimals
            )
            valid = (
                isinstance(value, int | float)
                and not isinstance(value, bool)
                and domain.is_executable(value)
            )
        if not valid:
            raise view_error("bayesian_view_holds_invalid", 422)


def evaluate_view(
    settings: Settings,
    receipts: BoViewReceiptStore,
    study_id: UUID,
    model_id: UUID,
    body: dto.ViewEvaluationRequest,
) -> dto.ViewEvaluationReceipt:
    from app.services.bo_loo import get_loo_view
    from app.services.bo_mixed_models import read_mixed_model
    from app.services.bo_mixed_studies import get_mixed_study

    started = monotonic()
    try:
        with receipts.calculation():
            identity = storage.model_source(settings.workspace_root, str(study_id), str(model_id))
            if (
                body.expected_model_sha256 != identity["snapshot_sha256"]
                or body.expected_history_sha256 != identity["history_sha256"]
            ):
                raise view_error("bayesian_view_source_changed")
            mixed = identity["schema_version"] == 2
            if identity["schema_version"] not in {1, 2}:
                raise view_error("bayesian_view_source_invalid")
            mixture = identity["study_schema_version"] == 8
            study: Any
            if mixture:
                from app.services.bo_mixture_studies import load_validated_mixture_study
                from app.services.bo_mixture_workflow import read_mixture_model

                study = load_validated_mixture_study(settings, str(study_id))
                record, snapshot, _ = read_mixture_model(settings, study, model_id)
            else:
                study = (
                    get_mixed_study(settings, study_id)
                    if mixed
                    else bo_planning.get_bayesian_study(settings, study_id)
                )
                record, snapshot, _ = (
                    read_mixed_model(settings, study, model_id)
                    if mixed
                    else bo_planning._read_model(settings, study, model_id)
                )
            source = _source(study_id, record)
            responses = [
                dto.ViewResponse.model_validate(
                    {key: row[key] for key in ("response_id", "name", "unit")}
                )
                for row in snapshot["calculation_request"]["objective"]["responses"]
            ]
            if isinstance(body, dto.ConditionalLooRequest):
                loo = get_loo_view(
                    settings,
                    study_id,
                    model_id,
                    LooRequest(
                        expected_model_sha256=body.expected_model_sha256,
                        expected_history_sha256=body.expected_history_sha256,
                    ),
                    mixed=mixed,
                )
                payload: dto.ViewPayload = dto.ConditionalLooPayload(
                    kind=body.kind,
                    source=source,
                    responses=responses,
                    calculation=loo.calculation,
                    calculation_sha256=loo.calculation_sha256,
                )
            elif mixture:
                from app.services.bo_mixture_views import mixture_matrix

                payload = mixture_matrix(study, snapshot, source, responses, body, started)
            else:
                payload = _matrix(study, record, snapshot, source, responses, body, mixed, started)
            return receipts.put(body.model_dump(mode="json"), payload)
    except BayesianStorageConflict as exc:
        raise view_error(exc.code) from exc


def _matrix(
    study: Any,
    record: dict[str, Any],
    snapshot: dict[str, Any],
    source: dto.ViewSource,
    responses: list[dto.ViewResponse],
    body: dto.ProfilerMatrixRequest,
    mixed: bool,
    started: float,
) -> dto.ProfilerMatrixPayload:
    _validate_holds(study.factors, body.holds)
    axes: list[dto.ProfileAxis] = []
    for factor in study.factors:
        values, available = _axis_values(factor, body.points_per_axis)
        points = [dict(body.holds, **{factor.factor_id: value}) for value in values]
        rows: list[dto.ProfilePoint] = []
        for offset in range(0, len(points), 100):
            budget = min(60000, int(body.time_budget_ms - (monotonic() - started) * 1000))
            if budget < 1000:
                raise view_error("bayesian_view_time_budget_exceeded")
            chunk = points[offset : offset + 100]
            evaluation = {"snapshot": snapshot, "points": chunk, "time_budget_ms": budget}
            if mixed:
                evaluation.update(max_moment_evaluations=65536, eligibility_excluded_encoded=[])
            else:
                evaluation["eligibility_excluded_normalized"] = []
            raw = bo_planning._run(
                "mixed_evaluate" if mixed else "evaluate", evaluation, time_budget_ms=budget
            )
            if (monotonic() - started) * 1000 > body.time_budget_ms:
                raise view_error("bayesian_view_time_budget_exceeded")
            try:
                parsed = [
                    (EvaluatedMixedCandidateRow if mixed else EvaluatedCandidateRow).model_validate(
                        row
                    )
                    for row in raw
                ]
                if len(parsed) != len(chunk):
                    raise ValueError
                for expected, row in zip(chunk, parsed, strict=True):
                    if row.input_coordinates != expected:
                        raise ValueError
                    rows.append(
                        dto.ProfilePoint.model_validate(
                            row.model_dump(
                                mode="json",
                                include=set(dto.ProfilePoint.model_fields),
                            )
                        )
                    )
            except (ValueError, TypeError, KeyError):
                raise view_error("bayesian_view_payload_invalid") from None
        axes.append(
            dto.ProfileAxis(
                factor_id=factor.factor_id,
                name=factor.name,
                unit=factor.unit,
                kind=factor.domain_kind,
                available_level_count=available,
                points=rows,
            )
        )
    return dto.ProfilerMatrixPayload(
        kind="profiler_matrix",
        source=source,
        holds=body.holds,
        responses=responses,
        axes=axes,
        policy="source_locked_conditional_profiler_matrix_v1",
        constraints=[
            BayesianLinearConstraintRequest.model_validate(
                row.model_dump(
                    mode="json",
                    include=set(BayesianLinearConstraintRequest.model_fields),
                )
            )
            for row in study.constraints
        ],
        point_count=sum(len(axis.points) for axis in axes),
        warnings=snapshot["warnings"],
    )


def save_view(
    settings: Settings,
    receipts: BoViewReceiptStore,
    study_id: UUID,
    body: dto.SaveViewRequest,
) -> dto.SavedView:
    try:
        old = storage.replay(settings.workspace_root, str(study_id), body)
        if old is not None:
            return old
        request, receipt = receipts.get(body.receipt_id)
        source = receipt.payload.source
        if (
            source.study_id != study_id
            or body.expected_model_sha256 != source.model_sha256
            or body.expected_request_sha256 != receipt.request_sha256
            or body.expected_view_sha256 != receipt.view_sha256
        ):
            raise view_error("bayesian_view_source_changed")
        save = body.model_dump(mode="json")
        return storage.insert_view(
            settings.workspace_root,
            str(study_id),
            {
                "view_id": str(uuid4()),
                "study_version_id": str(source.study_version_id),
                "model_id": str(source.model_id),
                "schema_version": 1,
                "request_id": str(body.request_id),
                "kind": receipt.payload.kind,
                "save_json": planning_json(save),
                "save_sha256": planning_sha(save),
                "config_json": planning_json(request),
                "config_sha256": receipt.request_sha256,
                "result_json": planning_json(receipt.payload.model_dump(mode="json")),
                "result_sha256": receipt.view_sha256,
                "created_at": utc_now(),
            },
        )
    except BayesianStorageConflict as exc:
        raise view_error(exc.code) from exc


def read_view(settings: Settings, study_id: UUID, view_id: UUID) -> dto.SavedView:
    try:
        return storage.read_view(settings.workspace_root, str(study_id), str(view_id))
    except BayesianStorageConflict as exc:
        raise view_error(exc.code, 404 if exc.code == "bayesian_view_not_found" else 409) from exc


def list_views(settings: Settings, study_id: UUID) -> dto.SavedViewList:
    try:
        values = storage.list_views(settings.workspace_root, str(study_id))
        return dto.SavedViewList(
            items=[
                dto.SavedViewSummary.model_validate(
                    value.model_dump(mode="json", include=set(dto.SavedViewSummary.model_fields)),
                )
                for value in values
            ]
        )
    except BayesianStorageConflict as exc:
        raise view_error(exc.code) from exc
