"""Read-only diagnostic of an exact saved numeric or mixed planning source."""

from typing import Any
from uuid import UUID

from app.api.v1.schemas.bo_loo import LooCalculation, LooRequest, LooView
from app.core.config import Settings
from app.services.bayesian_noise_recommendations import _error
from app.services.bayesian_studies import get_bayesian_study
from app.services.bo_planning import _current, _read_model, _run
from app.storage.bo_planning import planning_sha


def get_loo_view(
    settings: Settings, study_id: UUID, model_id: UUID, body: LooRequest, *, mixed: bool = False
) -> LooView:
    from app.services.bo_mixture_studies import (
        is_mixture_study,
        load_validated_mixture_study,
        mixture_study_response,
    )

    mixture = is_mixture_study(settings, str(study_id))
    study: Any
    if mixture:
        from app.services.bo_mixture_workflow import read_mixture_model

        bundle = load_validated_mixture_study(settings, str(study_id))
        record, snapshot, _ = read_mixture_model(settings, bundle, model_id)
        study = mixture_study_response(bundle)
    elif mixed:
        from app.services.bo_mixed_models import read_mixed_model
        from app.services.bo_mixed_studies import get_mixed_study

        study = get_mixed_study(settings, study_id)
        record, snapshot, _ = read_mixed_model(settings, study, model_id)
    else:
        study = get_bayesian_study(settings, study_id)
        record, snapshot, _ = _read_model(settings, study, model_id)
    if (
        body.expected_model_sha256 != record["snapshot_sha256"]
        or body.expected_history_sha256 != record["history_sha256"]
    ):
        raise _error("bayesian_candidate_source_changed")
    result = _run("loo", {"snapshot": snapshot, "mixed": mixed})
    # A concurrent observation can advance the head while the worker reads its
    # immutable snapshot. Refresh only status, never replace the diagnostic source.
    current = (
        mixture_study_response(load_validated_mixture_study(settings, str(study_id)))
        if mixture
        else get_mixed_study(settings, study_id)
        if mixed
        else get_bayesian_study(settings, study_id)
    )
    try:
        calculation = LooCalculation.model_validate(result)
        source = snapshot["calculation_request"]
        expected_responses = [row["response_id"] for row in source["objective"]["responses"]]
        if [row.response_id for row in calculation.responses] != expected_responses:
            raise ValueError
        for response in calculation.responses:
            if [(str(row.trial_id), row.observed) for row in response.points] != [
                (row["trial_id"], row["response_values"][response.response_id])
                for row in source["observations"]
            ]:
                raise ValueError
        return LooView(
            study_id=study_id,
            model_id=model_id,
            model_sha256=record["snapshot_sha256"],
            config_sha256=record["config_sha256"],
            source_history_revision_id=record["source_history_revision_id"],
            history_sha256=record["history_sha256"],
            source_is_current=_current(current, record),
            calculation_sha256=planning_sha(calculation.model_dump(mode="json")),
            calculation=calculation,
        )
    except (ValueError, TypeError, KeyError):
        raise _error("bayesian_loo_diagnostic_invalid") from None
