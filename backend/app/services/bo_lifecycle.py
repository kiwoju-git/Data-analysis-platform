"""Dispatch source/trial presentation only; lifecycle transactions remain shared."""

from typing import Any

from app.core.config import Settings


def load_lifecycle_study(settings: Settings, study_id: str) -> Any:
    from app.services.bayesian_studies import _load_validated_study
    from app.services.bo_mixed_studies import is_mixed_study, load_validated_mixed_study
    from app.services.bo_mixture_studies import is_mixture_study, load_validated_mixture_study

    if is_mixture_study(settings, study_id):
        return load_validated_mixture_study(settings, study_id)

    reader = (
        load_validated_mixed_study if is_mixed_study(settings, study_id) else _load_validated_study
    )
    return reader(settings, study_id)


def observation_batch_response(bundle: Any, **fields: Any) -> Any:
    from app.api.v1.schemas.bayesian import BayesianObservationBatchCreateResponse
    from app.api.v1.schemas.bo_mixed_studies import MixedObservationBatchResponse
    from app.services.bayesian_studies import _study_response
    from app.services.bo_mixed_studies import mixed_study_response

    if bundle.version.schema_version == 8:
        from app.api.v1.schemas.bo_mixture_lifecycle import MixtureObservationBatchResponse
        from app.services.bo_mixture_studies import mixture_study_response

        return MixtureObservationBatchResponse(study=mixture_study_response(bundle), **fields)

    if bundle.version.schema_version == 7:
        return MixedObservationBatchResponse(study=mixed_study_response(bundle), **fields)
    return BayesianObservationBatchCreateResponse(
        batch_schema_version=1, study=_study_response(bundle), **fields
    )


def trial_transition_response(bundle: Any, trial: Any) -> Any:
    from app.api.v1.schemas.bayesian import BayesianTrialTransitionResponse
    from app.api.v1.schemas.bo_mixed_studies import MixedTrialTransitionResponse
    from app.services.bayesian_studies import _history_response, _trial_response
    from app.services.bo_mixed_studies import mixed_trial_response

    fields = {
        "study_id": bundle.study.study_id,
        "observation_history": _history_response(bundle.current_history),
    }
    if bundle.version.schema_version == 8:
        from app.api.v1.schemas.bo_mixture_lifecycle import MixtureTrialTransitionResponse
        from app.services.bo_mixture_studies import mixture_trial_response

        return MixtureTrialTransitionResponse(trial=mixture_trial_response(bundle, trial), **fields)
    if bundle.version.schema_version == 7:
        return MixedTrialTransitionResponse(trial=mixed_trial_response(bundle, trial), **fields)
    return BayesianTrialTransitionResponse(trial=_trial_response(trial), **fields)
