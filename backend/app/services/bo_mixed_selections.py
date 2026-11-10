"""Immutable ordered/automatic selections from exact mixed candidate revisions."""

from typing import Any
from uuid import UUID, uuid4

from pydantic import TypeAdapter

from app.api.v1.schemas.bo_mixed_planning import (
    MixedCandidateRow,
    MixedPlanningSelectionCalculation,
)
from app.api.v1.schemas.bo_mixed_workflow import (
    MixedAugmentationCalculation,
    MixedSelectionCalculation,
    MixedSelectionList,
    MixedSelectionRequest,
    MixedSelectionResponse,
    MixedSelectionSummary,
)
from app.core.config import Settings
from app.services.analysis_run_execution import utc_now
from app.services.bayesian_noise_recommendations import _error
from app.services.bo_mixed_candidates import mixed_excluded, read_mixed_candidate
from app.services.bo_mixed_models import calculation_factors, read_mixed_model, require_mixed_source
from app.services.bo_mixed_studies import get_mixed_study
from app.services.bo_planning import _current, _not_found, _run
from app.storage import bo_planning as storage
from app.storage.bayesian_studies import BayesianStorageConflict

_RESULT: TypeAdapter[MixedPlanningSelectionCalculation | MixedAugmentationCalculation] = (
    TypeAdapter(MixedSelectionCalculation)
)


def selection_rows(result: Any) -> list[Any]:
    return result.items if result.schema_version == 2 else result.selected_rows


def read_mixed_selection(
    settings: Settings, study: Any, selection_id: UUID
) -> tuple[dict[str, Any], MixedSelectionRequest, Any]:
    try:
        record = storage.get_planning_selection(
            settings.workspace_root, str(selection_id), str(study.study_version_id)
        )
        if record is None:
            raise _not_found()
        body = MixedSelectionRequest.model_validate_json(record["config_json"])
        result = _RESULT.validate_json(record["result_json"])
        require_mixed_source(study, body, current=False)
        candidate, rows, candidate_body = read_mixed_candidate(
            settings, study, body.candidate_revision_id
        )
        by_id = {row.row_id: row for row in rows}
        selected = selection_rows(result)
        if (
            record["schema_version"] != 3
            or record["request_id"] != str(body.request_id)
            or record["model_id"] != (str(body.model_id) if body.model_id else None)
            or record["candidate_revision_id"] != str(body.candidate_revision_id)
            or candidate["rows_sha256"] != body.expected_rows_sha256
            or candidate["source_trial_count"] != body.expected_trial_count
            or candidate["definition_sha256"] != body.expected_definition_sha256
            or candidate["source_history_revision_id"] != str(body.expected_history_revision_id)
            or candidate["history_sha256"] != body.expected_history_sha256
            or body.duplicate_tolerance != candidate_body.duplicate_tolerance
            or body.ordinal_rank_distance != candidate_body.ordinal_rank_distance
            or storage.planning_json(body.model_dump(mode="json")) != record["config_json"]
            or storage.planning_json(result.model_dump(mode="json")) != record["result_json"]
            or len(selected) != body.batch_size
            or (body.kind == "manual_ordered") != (result.schema_version == 2)
            or result.schema_version == 2
            and [row.row_id for row in selected] != body.row_ids
        ):
            raise ValueError
        snapshot = None
        if body.model_id is not None:
            model, snapshot, _ = read_mixed_model(settings, study, body.model_id)
            if model["snapshot_sha256"] != body.expected_model_sha256 or any(
                model[key] != candidate[key]
                for key in ("definition_sha256", "source_history_revision_id", "history_sha256")
            ):
                raise ValueError
        for row in selected:
            original = by_id[row.row_id]
            if not row.eligible or any(
                getattr(row, key) != getattr(original, key)
                for key in MixedCandidateRow.model_fields
            ):
                raise ValueError
        if result.schema_version == 2:
            assert snapshot is not None
            raw = snapshot["calculation_request"]
            if (
                result.max_moment_evaluations != body.max_moment_evaluations
                or result.ordinal_rank_distance != body.ordinal_rank_distance
            ):
                raise ValueError
            for step, row in enumerate(selected):
                sampler = row.planning.sampler
                if (
                    sampler.batch_step != step
                    or sampler.root_seed != raw["search"]["random_seed"]
                    or sampler.requested_sample_count != body.sample_count
                    or sampler.effective_sample_count != (body.sample_count if step else 0)
                    or sampler.conditioned_on_selected_ranks != list(range(1, step + 1))
                    or sampler.baseline_threshold
                    != snapshot["incumbent"]["latent_incumbent_value"] + raw["xi_desirability"]
                    or row.acquisition.xi_desirability != raw["xi_desirability"]
                    or row.nearest_selected_distance is not None
                    and (
                        row.nearest_selected_distance <= body.duplicate_tolerance
                        or row.nearest_selected_distance < body.min_batch_distance
                    )
                ):
                    raise ValueError
        if result.schema_version == 3:
            expected_source = augmentation_source(body)
            if (
                result.augmentation.source.model_dump(mode="json") != expected_source
                or result.augmentation.policy != body.policy
                or result.source_row_count != len(rows)
                or result.augmentation.ordinal_rank_distance != body.ordinal_rank_distance
                or result.max_moment_evaluations != body.max_moment_evaluations
                or result.time_budget_ms != body.time_budget_ms
                or result.augmentation.max_evaluations != body.max_evaluations
            ):
                raise ValueError
        return record, body, result
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    except (ValueError, TypeError, KeyError, AttributeError):
        raise _error("bayesian_planning_artifact_invalid") from None


def augmentation_source(body: MixedSelectionRequest) -> dict[str, Any]:
    return {
        "model_snapshot_id": str(body.model_id) if body.model_id else None,
        "model_snapshot_sha256": body.expected_model_sha256,
        "candidate_revision_id": str(body.candidate_revision_id),
        "candidate_revision_sha256": body.expected_rows_sha256,
        "history_sha256": body.expected_history_sha256,
    }


def get_mixed_selection(
    settings: Settings, study_id: UUID, selection_id: UUID
) -> MixedSelectionResponse:
    study = get_mixed_study(settings, study_id)
    record, body, result = read_mixed_selection(settings, study, selection_id)
    source = {
        "definition_sha256": body.expected_definition_sha256,
        "source_history_revision_id": str(body.expected_history_revision_id),
        "history_sha256": body.expected_history_sha256,
    }
    return MixedSelectionResponse(
        selection_id=selection_id,
        study_id=study_id,
        study_version_id=study.study_version_id,
        model_id=body.model_id,
        candidate_revision_id=body.candidate_revision_id,
        config_sha256=record["config_sha256"],
        result_sha256=record["result_sha256"],
        request=body,
        calculation=result,
        created_at=record["created_at"],
        source_is_current=_current(study, source, body.expected_trial_count),
        confirmed_batch_id=record["confirmed_batch_id"],
    )


def create_mixed_selection(
    settings: Settings, study_id: UUID, body: MixedSelectionRequest
) -> MixedSelectionResponse:
    study = get_mixed_study(settings, study_id)
    config = body.model_dump(mode="json")
    try:
        old = storage.find_planning_request(
            settings.workspace_root,
            str(study.study_version_id),
            str(body.request_id),
            kind="selection",
        )
        if old is not None:
            if old["schema_version"] != 3 or old["config_sha256"] != storage.planning_sha(config):
                raise _error("bayesian_planning_request_conflict")
            return get_mixed_selection(settings, study_id, UUID(old["selection_id"]))
        require_mixed_source(study, body)
        candidate, rows, candidate_body = read_mixed_candidate(
            settings, study, body.candidate_revision_id
        )
        if (
            candidate["rows_sha256"] != body.expected_rows_sha256
            or candidate["source_trial_count"] != body.expected_trial_count
            or candidate["source_history_revision_id"] != str(body.expected_history_revision_id)
            or candidate["history_sha256"] != body.expected_history_sha256
            or candidate_body.duplicate_tolerance != body.duplicate_tolerance
            or candidate_body.ordinal_rank_distance != body.ordinal_rank_distance
        ):
            raise _error("bayesian_candidate_source_changed")
        if any(trial.state == "pending" for trial in study.trials):
            raise _error("bayesian_optimization_pending_recommendation_exists")
        if len(study.trials) + body.batch_size > body.total_trial_budget:
            raise _error("bayesian_optimization_batch_budget_exceeded")
        snapshot = None
        if body.model_id is not None:
            model, snapshot, model_body = read_mixed_model(settings, study, body.model_id)
            require_mixed_source(study, model_body)
            if (
                model["snapshot_sha256"] != body.expected_model_sha256
                or model_body.fit.search.duplicate_tolerance != body.duplicate_tolerance
            ):
                raise _error("bayesian_planning_model_mismatch")
        by_id = {row.row_id: row for row in rows}
        excluded = [
            [row[f.factor_id] for f in study.factors]
            for row in mixed_excluded(study, body.expected_trial_count)
        ]
        payload: dict[str, Any]
        if body.kind == "manual_ordered":
            if any(key not in by_id or not by_id[key].eligible for key in body.row_ids):
                raise _error("bayesian_planning_selection_ineligible")
            payload = {
                "snapshot": snapshot,
                "points": [by_id[key].actual_coordinates for key in body.row_ids],
                "eligibility_excluded_encoded": excluded,
                "ordinal_rank_distance": body.ordinal_rank_distance,
                "sample_count": body.sample_count,
                "min_batch_distance": body.min_batch_distance,
                "max_moment_evaluations": body.max_moment_evaluations,
                "time_budget_ms": body.time_budget_ms,
            }
            result = _run("mixed_selection", payload, time_budget_ms=body.time_budget_ms)
            selected = result["items"]
        else:
            payload = {
                "factors": calculation_factors(study),
                "constraints": [row.model_dump(mode="json") for row in study.constraints],
                "points": [row.actual_coordinates for row in rows],
                "existing_coordinates": excluded,
                "source": augmentation_source(body),
                "snapshot": snapshot,
                "policy": body.policy,
                **{
                    key: getattr(body, key)
                    for key in (
                        "batch_size",
                        "duplicate_tolerance",
                        "ordinal_rank_distance",
                        "min_batch_distance",
                        "max_evaluations",
                        "max_moment_evaluations",
                        "time_budget_ms",
                    )
                },
            }
            result = _run("mixed_augmentation", payload, time_budget_ms=body.time_budget_ms)
            selected = result["selected_rows"]
        for item in selected:
            row = by_id[item["row_id"]]
            item["source_row_number"], item["input_coordinates"] = (
                row.source_row_number,
                row.input_coordinates,
            )
        result = _RESULT.validate_python(result).model_dump(mode="json")
        record = {
            "selection_id": str(uuid4()),
            "study_version_id": str(study.study_version_id),
            "model_id": str(body.model_id) if body.model_id else None,
            "candidate_revision_id": str(body.candidate_revision_id),
            "request_id": str(body.request_id),
            "schema_version": 3,
            "config_json": storage.planning_json(config),
            "config_sha256": storage.planning_sha(config),
            "result_json": storage.planning_json(result),
            "result_sha256": storage.planning_sha(result),
            "created_at": utc_now(),
        }
        identity = storage.insert_planning_selection(settings.workspace_root, record)
        return get_mixed_selection(settings, study_id, UUID(identity))
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc


def list_mixed_selections(settings: Settings, study_id: UUID) -> MixedSelectionList:
    study = get_mixed_study(settings, study_id)
    records = storage.list_mixed_selection_summaries(
        settings.workspace_root, str(study.study_version_id)
    )
    return MixedSelectionList(
        items=[
            MixedSelectionSummary.model_validate(
                {
                    **{
                        key: row[key]
                        for key in MixedSelectionSummary.model_fields
                        if key not in {"schema_version", "study_id", "source_is_current"}
                    },
                    "study_id": study_id,
                    "source_is_current": _current(study, row, row["source_trial_count"]),
                }
            )
            for row in records
        ]
    )
