from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.api.v1.schemas.bayesian import (
    BayesianHistoryListResponse,
    BayesianHistoryRevisionResponse,
    BayesianLatestRecommendationResponse,
    BayesianObservationCreateRequest,
    BayesianRecommendationCreateRequest,
    BayesianRecommendationListResponse,
    BayesianRecommendationResponse,
    BayesianStudyCloseRequest,
    BayesianStudyCloseResponse,
    BayesianStudyCreateRequest,
    BayesianStudyDeleteRequest,
    BayesianStudyDeleteResponse,
    BayesianStudyDeletionPreflightResponse,
    BayesianStudyListResponse,
    BayesianStudyResponse,
    BayesianTrialAbandonRequest,
    BayesianTrialListResponse,
    BayesianTrialTransitionResponse,
)
from app.services.bayesian_recommendations import (
    create_bayesian_recommendation,
    get_bayesian_recommendation,
    get_latest_bayesian_recommendation,
    list_bayesian_recommendations,
)
from app.services.bayesian_studies import (
    abandon_bayesian_trial,
    close_bayesian_study,
    complete_bayesian_trial,
    create_bayesian_study,
    delete_bayesian_study,
    get_bayesian_history,
    get_bayesian_study,
    get_bayesian_study_deletion_preflight,
    list_bayesian_history,
    list_bayesian_studies,
    list_bayesian_trials,
)

router = APIRouter(prefix="/bayesian-studies", tags=["bayesian-studies"])


@router.post(
    "",
    response_model=BayesianStudyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bayesian_study_route(
    request: Request, body: BayesianStudyCreateRequest
) -> BayesianStudyResponse:
    return create_bayesian_study(request.app.state.settings, body)


@router.get("", response_model=BayesianStudyListResponse)
def list_bayesian_studies_route(
    request: Request,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> BayesianStudyListResponse:
    return list_bayesian_studies(request.app.state.settings, offset=offset, limit=limit)


@router.get("/{study_id}", response_model=BayesianStudyResponse)
def get_bayesian_study_route(request: Request, study_id: UUID) -> BayesianStudyResponse:
    return get_bayesian_study(request.app.state.settings, study_id)


@router.get(
    "/{study_id}/deletion-preflight",
    response_model=BayesianStudyDeletionPreflightResponse,
)
def get_bayesian_study_deletion_preflight_route(
    request: Request,
    study_id: UUID,
) -> BayesianStudyDeletionPreflightResponse:
    return get_bayesian_study_deletion_preflight(request.app.state.settings, study_id)


@router.delete("/{study_id}", response_model=BayesianStudyDeleteResponse)
def delete_bayesian_study_route(
    request: Request,
    study_id: UUID,
    body: BayesianStudyDeleteRequest,
) -> BayesianStudyDeleteResponse:
    return delete_bayesian_study(request.app.state.settings, study_id, body)


@router.post("/{study_id}/close", response_model=BayesianStudyCloseResponse)
def close_bayesian_study_route(
    request: Request,
    study_id: UUID,
    body: BayesianStudyCloseRequest,
) -> BayesianStudyCloseResponse:
    return close_bayesian_study(request.app.state.settings, study_id, body)


@router.get("/{study_id}/trials", response_model=BayesianTrialListResponse)
def list_bayesian_trials_route(
    request: Request,
    study_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> BayesianTrialListResponse:
    return list_bayesian_trials(
        request.app.state.settings,
        study_id,
        offset=offset,
        limit=limit,
    )


@router.put(
    "/{study_id}/trials/{trial_id}/observation",
    response_model=BayesianTrialTransitionResponse,
)
def complete_bayesian_trial_route(
    request: Request,
    study_id: UUID,
    trial_id: UUID,
    body: BayesianObservationCreateRequest,
) -> BayesianTrialTransitionResponse:
    return complete_bayesian_trial(request.app.state.settings, study_id, trial_id, body)


@router.post(
    "/{study_id}/trials/{trial_id}/abandon",
    response_model=BayesianTrialTransitionResponse,
)
def abandon_bayesian_trial_route(
    request: Request,
    study_id: UUID,
    trial_id: UUID,
    body: BayesianTrialAbandonRequest | None = None,
) -> BayesianTrialTransitionResponse:
    return abandon_bayesian_trial(request.app.state.settings, study_id, trial_id, body)


@router.get("/{study_id}/history", response_model=BayesianHistoryListResponse)
def list_bayesian_history_route(
    request: Request,
    study_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> BayesianHistoryListResponse:
    return list_bayesian_history(
        request.app.state.settings,
        study_id,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{study_id}/history/{history_revision_id}",
    response_model=BayesianHistoryRevisionResponse,
)
def get_bayesian_history_route(
    request: Request, study_id: UUID, history_revision_id: UUID
) -> BayesianHistoryRevisionResponse:
    return get_bayesian_history(request.app.state.settings, study_id, history_revision_id)


@router.post(
    "/{study_id}/recommendations",
    response_model=BayesianRecommendationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bayesian_recommendation_route(
    request: Request,
    study_id: UUID,
    body: BayesianRecommendationCreateRequest,
) -> BayesianRecommendationResponse:
    return create_bayesian_recommendation(request.app.state.settings, study_id, body)


@router.get(
    "/{study_id}/recommendations",
    response_model=BayesianRecommendationListResponse,
)
def list_bayesian_recommendations_route(
    request: Request,
    study_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> BayesianRecommendationListResponse:
    return list_bayesian_recommendations(
        request.app.state.settings,
        study_id,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{study_id}/recommendations/latest",
    response_model=BayesianLatestRecommendationResponse,
)
def get_latest_bayesian_recommendation_route(
    request: Request,
    study_id: UUID,
) -> BayesianLatestRecommendationResponse:
    return get_latest_bayesian_recommendation(
        request.app.state.settings,
        study_id,
    )


@router.get(
    "/{study_id}/recommendations/{recommendation_id}",
    response_model=BayesianRecommendationResponse,
)
def get_bayesian_recommendation_route(
    request: Request,
    study_id: UUID,
    recommendation_id: UUID,
) -> BayesianRecommendationResponse:
    return get_bayesian_recommendation(
        request.app.state.settings,
        study_id,
        recommendation_id,
    )
