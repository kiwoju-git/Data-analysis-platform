import hashlib
import json
import math
from typing import Final
from uuid import UUID

from pydantic import ValidationError

from app.analyses.registry import METHOD_VERSIONS
from app.api.v1.schemas.bayesian import (
    BayesianFactorResponse,
    BayesianLinearConstraintResponse,
    BayesianRecommendationCreateRequest,
    BayesianRecommendationResponse,
    BayesianTrialResponse,
)
from app.services.analysis_run_execution import canonical_json_bytes
from app.storage.bayesian_studies import BayesianRecommendationRecord

BAYESIAN_METHOD_ID: Final = "doe.bayesian_optimization"
SUPPORTED_BAYESIAN_RECOMMENDATION_METHOD_VERSIONS: Final = frozenset(
    {"0.2.0", "0.2.1", METHOD_VERSIONS[BAYESIAN_METHOD_ID]}
)


def recommendation_trial_snapshot_matches(
    *,
    snapshot: BayesianTrialResponse,
    current: BayesianTrialResponse,
) -> bool:
    return (
        snapshot.state == "pending"
        and snapshot.objective_value is None
        and snapshot.closed_at is None
        and snapshot.trial_id == current.trial_id
        and snapshot.study_version_id == current.study_version_id
        and snapshot.trial_number == current.trial_number
        and snapshot.origin == current.origin == "recommendation"
        and snapshot.actual_coordinates == current.actual_coordinates
        and snapshot.normalized_coordinates == current.normalized_coordinates
        and snapshot.coordinates_sha256 == current.coordinates_sha256
        and snapshot.created_at == current.created_at
    )


def validate_bayesian_recommendation_record(
    *,
    record: BayesianRecommendationRecord,
    study_id: str,
    study_version_id: str,
    definition_sha256: str,
    source_history_revision_id: str,
    source_history_sha256: str,
    source_observation_values: list[float],
    factors: list[BayesianFactorResponse],
    constraints: list[BayesianLinearConstraintResponse],
    objective_direction: str,
    current_trial: BayesianTrialResponse,
) -> BayesianRecommendationResponse:
    try:
        response = BayesianRecommendationResponse.model_validate_json(record.result_json)
        config = json.loads(record.config_json)
        request = BayesianRecommendationCreateRequest.model_validate(config.get("request"))
    except (ValidationError, AttributeError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("bayesian recommendation payload is invalid") from exc
    result_payload_sha256 = hashlib.sha256(
        canonical_json_bytes(response.result.model_dump(mode="json"))
    ).hexdigest()
    provenance = response.provenance
    expected_direction_multiplier = (
        1.0 if response.result.objective_direction == "maximize" else -1.0
    )
    if (
        not isinstance(config, dict)
        or record.study_version_id != study_version_id
        or record.trial_id != str(current_trial.trial_id)
        or record.source_history_revision_id != source_history_revision_id
        or record.source_observation_history_sha256 != source_history_sha256
        or record.method_id != BAYESIAN_METHOD_ID
        or record.method_version not in SUPPORTED_BAYESIAN_RECOMMENDATION_METHOD_VERSIONS
        or record.config_schema_version != 1
        or record.result_schema_version != 1
        or record.model_schema_version != 1
        or hashlib.sha256(record.config_json.encode("utf-8")).hexdigest() != record.config_sha256
        or hashlib.sha256(record.result_json.encode("utf-8")).hexdigest() != record.result_sha256
        or result_payload_sha256 != record.result_payload_sha256
        or response.recommendation_id != UUID(record.recommendation_id)
        or response.study_id != UUID(study_id)
        or response.study_version_id != UUID(study_version_id)
        or response.source_history_revision_id != UUID(source_history_revision_id)
        or response.source_observation_history_sha256 != source_history_sha256
        or response.definition_sha256 != definition_sha256
        or response.method_id != record.method_id
        or response.method_version != record.method_version
        or response.config_schema_version != record.config_schema_version
        or response.result_schema_version != record.result_schema_version
        or response.model_schema_version != record.model_schema_version
        or response.config_sha256 != record.config_sha256
        or response.result_payload_sha256 != result_payload_sha256
        or response.created_at != record.created_at
        or response.trial.created_at != response.created_at
        or not recommendation_trial_snapshot_matches(
            snapshot=response.trial,
            current=current_trial,
        )
        or not _result_matches_source_context(
            response=response,
            request=request,
            source_observation_values=source_observation_values,
            factors=factors,
            constraints=constraints,
            objective_direction=objective_direction,
        )
        or response.result.model.schema_version != record.model_schema_version
        or response.result.model.objective_direction_multiplier != expected_direction_multiplier
        or config.get("schema_version") != record.config_schema_version
        or config.get("study_id") != study_id
        or config.get("study_version_id") != study_version_id
        or config.get("definition_sha256") != definition_sha256
        or config.get("source_history_revision_id") != source_history_revision_id
        or config.get("source_observation_history_sha256") != source_history_sha256
        or str(request.expected_history_revision_id) != source_history_revision_id
        or provenance.study_id != response.study_id
        or provenance.study_version_id != response.study_version_id
        or provenance.recommendation_id != response.recommendation_id
        or provenance.recommendation_trial_id != response.trial.trial_id
        or provenance.source_history_revision_id != response.source_history_revision_id
        or provenance.source_observation_history_sha256 != source_history_sha256
        or provenance.definition_sha256 != definition_sha256
        or provenance.method_id != record.method_id
        or provenance.method_version != record.method_version
        or provenance.config_schema_version != record.config_schema_version
        or provenance.result_schema_version != record.result_schema_version
        or provenance.model_schema_version != record.model_schema_version
        or provenance.app_version != record.app_version
        or provenance.package_versions != response.result.model.package_versions
        or provenance.created_at != record.created_at
    ):
        raise ValueError("bayesian recommendation relationship mismatch")
    return response


def _result_matches_source_context(
    *,
    response: BayesianRecommendationResponse,
    request: BayesianRecommendationCreateRequest,
    source_observation_values: list[float],
    factors: list[BayesianFactorResponse],
    constraints: list[BayesianLinearConstraintResponse],
    objective_direction: str,
) -> bool:
    result = response.result
    model = result.model
    budget = result.budget
    search = request.search
    factor_ids = [factor.factor_id for factor in factors]
    if (
        not source_observation_values
        or any(not math.isfinite(value) for value in source_observation_values)
        or set(result.recommended_actual_coordinates) != set(factor_ids)
        or set(result.recommended_normalized_coordinates) != set(factor_ids)
        or result.recommended_actual_coordinates != response.trial.actual_coordinates
        or result.recommended_normalized_coordinates != response.trial.normalized_coordinates
        or result.objective_direction != objective_direction
        or model.completed_observation_count != len(source_observation_values)
        or model.jitter != float(search.jitter)
        or model.hyperparameter_restart_count != search.hyperparameter_restart_count
        or model.model_evaluations != budget.model_evaluations_consumed
        or model.fit_elapsed_ms > budget.elapsed_ms
        or budget.candidate_count_requested != search.candidate_count
        or budget.local_start_count_requested != search.local_start_count
        or budget.max_evaluations != search.max_evaluations
        or budget.model_max_iterations != search.model_max_iterations
        or budget.model_max_evaluations != search.model_max_evaluations
        or budget.time_budget_ms != search.time_budget_ms
        or budget.feasible_candidate_count > budget.candidate_count_requested
        or budget.local_starts_attempted > budget.local_start_count_requested
        or budget.local_success_count > budget.local_starts_attempted
        or budget.evaluations_consumed > budget.max_evaluations
        or budget.model_evaluations_consumed > budget.model_max_evaluations
        or "bayesian_optimization_confirmation_required" not in result.warnings
        or "bayesian_optimization_no_global_optimum_guarantee" not in result.warnings
    ):
        return False
    incumbent = (
        max(source_observation_values)
        if objective_direction == "maximize"
        else min(source_observation_values)
    )
    if not math.isclose(result.incumbent_objective, incumbent, rel_tol=1e-12, abs_tol=1e-12):
        return False
    for factor in factors:
        normalized = result.recommended_normalized_coordinates[factor.factor_id]
        actual = result.recommended_actual_coordinates[factor.factor_id]
        expected_actual = factor.low + normalized * (factor.high - factor.low)
        if (
            not math.isfinite(normalized)
            or not math.isfinite(actual)
            or normalized < 0.0
            or normalized > 1.0
            or not math.isclose(actual, expected_actual, rel_tol=1e-12, abs_tol=1e-12)
        ):
            return False
    if len(result.constraint_evaluations) != len(constraints):
        return False
    for stored, constraint in zip(result.constraint_evaluations, constraints, strict=True):
        lhs = sum(
            term.coefficient * result.recommended_actual_coordinates[term.factor_id]
            for term in constraint.terms
        )
        tolerance = 1e-10 * max(1.0, abs(lhs), abs(constraint.bound))
        slack = constraint.bound - lhs
        satisfied = lhs <= constraint.bound + tolerance
        if constraint.relation == "greater_than_or_equal":
            slack = lhs - constraint.bound
            satisfied = lhs >= constraint.bound - tolerance
        if (
            stored.constraint_id != constraint.constraint_id
            or stored.name != constraint.name
            or stored.relation != constraint.relation
            or not math.isclose(stored.lhs, lhs, rel_tol=1e-12, abs_tol=1e-12)
            or not math.isclose(stored.bound, constraint.bound, rel_tol=1e-12, abs_tol=1e-12)
            or not math.isclose(stored.slack, slack, rel_tol=1e-12, abs_tol=1e-12)
            or stored.satisfied != satisfied
            or not stored.satisfied
        ):
            return False
    numeric_values = (
        result.predicted_objective_mean,
        result.posterior_standard_deviation,
        result.expected_improvement,
        result.incumbent_objective,
        model.constant_value,
        model.log_marginal_likelihood,
        model.objective_direction_multiplier,
        model.objective_normalization_mean,
        model.objective_normalization_scale,
        model.jitter,
        model.fit_elapsed_ms,
        budget.elapsed_ms,
    )
    return all(math.isfinite(value) for value in numeric_values) and all(
        math.isfinite(value) and value > 0.0 for value in model.length_scales
    )
