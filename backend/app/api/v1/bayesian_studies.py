from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, status

from app.api.v1.schemas.bayesian import (
    BayesianHistoryListResponse,
    BayesianHistoryRevisionResponse,
    BayesianLatestRecommendationResponse,
    BayesianObservationBatchCreateRequest,
    BayesianObservationBatchCreateResponse,
    BayesianObservationCreateRequest,
    BayesianRecommendationBatchCreateRequest,
    BayesianRecommendationCreateRequest,
    BayesianRecommendationListResponse,
    BayesianRecommendationResponse,
    BayesianReplicateCreateRequest,
    BayesianReplicateCreateResponse,
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
from app.api.v1.schemas.bayesian_batches import (
    BayesianAnyBatchListResponse,
    BayesianAnyBatchResponse,
    BayesianAnyLatestBatchResponse,
)
from app.api.v1.schemas.bayesian_desirability_recommendations import (
    DesirabilityAnyBatchResponse as DesirabilityBatchResponse,
)
from app.api.v1.schemas.bayesian_desirability_recommendations import (
    DesirabilityAnyLatestResponse as DesirabilityLatestResponse,
)
from app.api.v1.schemas.bayesian_desirability_recommendations import (
    DesirabilityAnyReviewRequest as DesirabilityReviewRequest,
)
from app.api.v1.schemas.bayesian_desirability_recommendations import (
    DesirabilityAnyReviewResponse as DesirabilityReviewResponse,
)
from app.api.v1.schemas.bayesian_noise import (
    BayesianAnyBatchResponse as ScalarBatchResponse,
)
from app.api.v1.schemas.bayesian_noise import (
    BayesianCurrentBatchRequest,
    BayesianCurrentBatchResponse,
    BayesianCurrentSingleRequest,
)
from app.api.v1.schemas.bayesian_review import (
    BayesianRecommendationReviewConfirmRequest,
    BayesianRecommendationReviewResponse,
)
from app.api.v1.schemas.bo_curve_preview import CurvePreviewRequest, CurvePreviewResponse
from app.api.v1.schemas.bo_dataset_import import (
    DatasetImportCreateRequest,
    DatasetImportPreflightRequest,
)
from app.api.v1.schemas.bo_dataset_source import DatasetImportPreflightResponse
from app.api.v1.schemas.bo_mixed_studies import (
    MixedObservationBatchResponse,
    MixedReplicateCreateResponse,
    MixedStudyCloseResponse,
    MixedStudyCreateRequest,
    MixedStudyResponse,
    MixedTrialListResponse,
    MixedTrialTransitionResponse,
)
from app.api.v1.schemas.bo_mixture import MixtureStudyResponse
from app.api.v1.schemas.bo_mixture_dataset_import import (
    MixtureDatasetImportCreateRequest,
    MixtureDatasetImportPreflightRequest,
    MixtureDatasetImportPreflightResponse,
)
from app.api.v1.schemas.bo_mixture_lifecycle import (
    MixtureObservationBatchResponse,
    MixtureReplicateCreateResponse,
    MixtureStudyCloseResponse,
    MixtureTrialListResponse,
    MixtureTrialTransitionResponse,
)
from app.services.bayesian_desirability_recommendations import (
    confirm_desirability_review,
    create_desirability_review,
    get_desirability_recommendation,
    latest_desirability_recommendation,
)
from app.services.bayesian_recommendation_batches import (
    create_bayesian_recommendation_batch,
    get_bayesian_recommendation_batch,
    get_latest_bayesian_recommendation_batch,
    list_bayesian_recommendation_batches,
)
from app.services.bayesian_recommendations import (
    create_bayesian_recommendation,
    get_bayesian_recommendation,
    get_latest_bayesian_recommendation,
    list_bayesian_recommendations,
)
from app.services.bayesian_replicates import create_bayesian_replicates
from app.services.bayesian_review import confirm_bayesian_review, create_bayesian_review
from app.services.bayesian_studies import (
    abandon_bayesian_trial,
    bayesian_initial_design_csv,
    close_bayesian_study,
    complete_bayesian_observations_batch,
    complete_bayesian_trial,
    create_bayesian_study,
    delete_bayesian_study,
    get_bayesian_history,
    get_bayesian_study_deletion_preflight,
    list_bayesian_history,
    list_bayesian_studies,
    list_bayesian_trials,
)
from app.services.bo_curve_preview import preview_target_curve
from app.services.bo_dataset_import import create_dataset_import, preflight_dataset_import

router = APIRouter(prefix="/bayesian-studies", tags=["bayesian-studies"])


@router.post(
    "/import-preflight",
    response_model=DatasetImportPreflightResponse | MixtureDatasetImportPreflightResponse,
)
def dataset_import_preflight_route(
    request: Request, body: DatasetImportPreflightRequest | MixtureDatasetImportPreflightRequest
) -> DatasetImportPreflightResponse | MixtureDatasetImportPreflightResponse:
    return preflight_dataset_import(request.app.state.settings, body)


@router.post(
    "/from-dataset",
    response_model=BayesianStudyResponse | MixedStudyResponse | MixtureStudyResponse,
    status_code=status.HTTP_201_CREATED,
)
def dataset_import_create_route(
    request: Request, body: DatasetImportCreateRequest | MixtureDatasetImportCreateRequest
) -> BayesianStudyResponse | MixedStudyResponse | MixtureStudyResponse:
    return create_dataset_import(request.app.state.settings, body)


@router.post("/target-curve-preview", response_model=CurvePreviewResponse)
def target_curve_preview_route(body: CurvePreviewRequest) -> CurvePreviewResponse:
    return preview_target_curve(body)


@router.post("/{study_id}/desirability-reviews", response_model=DesirabilityReviewResponse)
def create_desirability_review_route(
    request: Request,
    study_id: UUID,
    body: DesirabilityReviewRequest,
) -> DesirabilityReviewResponse:
    return create_desirability_review(
        request.app.state.settings,
        request.app.state.bayesian_reviews,
        study_id,
        body,
    )


@router.post(
    "/{study_id}/desirability-reviews/{review_id}/confirm",
    response_model=DesirabilityBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_desirability_review_route(
    request: Request,
    study_id: UUID,
    review_id: UUID,
    body: BayesianRecommendationReviewConfirmRequest,
) -> DesirabilityBatchResponse:
    return confirm_desirability_review(
        request.app.state.settings,
        request.app.state.bayesian_reviews,
        study_id,
        review_id,
        body,
    )


@router.get(
    "/{study_id}/desirability-recommendations/latest", response_model=DesirabilityLatestResponse
)
def latest_desirability_recommendation_route(
    request: Request, study_id: UUID
) -> DesirabilityLatestResponse:
    return latest_desirability_recommendation(request.app.state.settings, study_id)


@router.get(
    "/{study_id}/desirability-recommendations/{batch_id}", response_model=DesirabilityBatchResponse
)
def get_desirability_recommendation_route(
    request: Request,
    study_id: UUID,
    batch_id: UUID,
) -> DesirabilityBatchResponse:
    return get_desirability_recommendation(request.app.state.settings, study_id, batch_id)


@router.post(
    "/{study_id}/recommendation-reviews",
    response_model=BayesianRecommendationReviewResponse,
)
def create_bayesian_review_route(
    request: Request, study_id: UUID, body: BayesianCurrentBatchRequest
) -> BayesianRecommendationReviewResponse:
    return create_bayesian_review(
        request.app.state.settings, request.app.state.bayesian_reviews, study_id, body
    )


@router.post(
    "/{study_id}/recommendation-reviews/{review_id}/confirm",
    response_model=BayesianCurrentBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_bayesian_review_route(
    request: Request,
    study_id: UUID,
    review_id: UUID,
    body: BayesianRecommendationReviewConfirmRequest,
) -> BayesianCurrentBatchResponse:
    return confirm_bayesian_review(
        request.app.state.settings, request.app.state.bayesian_reviews, study_id, review_id, body
    )


@router.post(
    "/{study_id}/trials/{trial_id}/replicates",
    response_model=BayesianReplicateCreateResponse
    | MixedReplicateCreateResponse
    | MixtureReplicateCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bayesian_replicates_route(
    request: Request,
    study_id: UUID,
    trial_id: UUID,
    body: BayesianReplicateCreateRequest,
) -> (
    BayesianReplicateCreateResponse | MixedReplicateCreateResponse | MixtureReplicateCreateResponse
):
    return create_bayesian_replicates(request.app.state.settings, study_id, trial_id, body)


@router.post(
    "",
    response_model=BayesianStudyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bayesian_study_route(
    request: Request, body: BayesianStudyCreateRequest
) -> BayesianStudyResponse:
    return create_bayesian_study(request.app.state.settings, body)


@router.post("/mixed", response_model=MixedStudyResponse, status_code=status.HTTP_201_CREATED)
def create_mixed_study_route(request: Request, body: MixedStudyCreateRequest) -> MixedStudyResponse:
    from app.services.bo_mixed_studies import create_mixed_study

    return create_mixed_study(request.app.state.settings, body)


@router.get("", response_model=BayesianStudyListResponse)
def list_bayesian_studies_route(
    request: Request,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> BayesianStudyListResponse:
    return list_bayesian_studies(request.app.state.settings, offset=offset, limit=limit)


@router.get("/{study_id}/initial-design.csv")
def export_bayesian_initial_design_route(request: Request, study_id: UUID) -> Response:
    content, filename = bayesian_initial_design_csv(request.app.state.settings, study_id)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/{study_id}", response_model=BayesianStudyResponse | MixedStudyResponse | MixtureStudyResponse
)
def get_bayesian_study_route(
    request: Request, study_id: UUID
) -> BayesianStudyResponse | MixedStudyResponse | MixtureStudyResponse:
    from app.services.bo_mixed_studies import get_any_bayesian_study

    return get_any_bayesian_study(request.app.state.settings, study_id)


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


@router.post(
    "/{study_id}/close",
    response_model=BayesianStudyCloseResponse | MixedStudyCloseResponse | MixtureStudyCloseResponse,
)
def close_bayesian_study_route(
    request: Request,
    study_id: UUID,
    body: BayesianStudyCloseRequest,
) -> BayesianStudyCloseResponse | MixedStudyCloseResponse | MixtureStudyCloseResponse:
    return close_bayesian_study(request.app.state.settings, study_id, body)


@router.get(
    "/{study_id}/trials",
    response_model=BayesianTrialListResponse | MixedTrialListResponse | MixtureTrialListResponse,
)
def list_bayesian_trials_route(
    request: Request,
    study_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> BayesianTrialListResponse | MixedTrialListResponse | MixtureTrialListResponse:
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


@router.put(
    "/{study_id}/observations/batch",
    response_model=BayesianObservationBatchCreateResponse
    | MixedObservationBatchResponse
    | MixtureObservationBatchResponse,
)
def complete_bayesian_observations_batch_route(
    request: Request,
    study_id: UUID,
    body: BayesianObservationBatchCreateRequest,
) -> (
    BayesianObservationBatchCreateResponse
    | MixedObservationBatchResponse
    | MixtureObservationBatchResponse
):
    return complete_bayesian_observations_batch(
        request.app.state.settings,
        study_id,
        body,
    )


@router.post(
    "/{study_id}/trials/{trial_id}/abandon",
    response_model=BayesianTrialTransitionResponse
    | MixedTrialTransitionResponse
    | MixtureTrialTransitionResponse,
)
def abandon_bayesian_trial_route(
    request: Request,
    study_id: UUID,
    trial_id: UUID,
    body: BayesianTrialAbandonRequest | None = None,
) -> (
    BayesianTrialTransitionResponse | MixedTrialTransitionResponse | MixtureTrialTransitionResponse
):
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
    response_model=BayesianRecommendationResponse | BayesianCurrentBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bayesian_recommendation_route(
    request: Request,
    study_id: UUID,
    body: BayesianRecommendationCreateRequest | BayesianCurrentSingleRequest,
) -> BayesianRecommendationResponse | BayesianCurrentBatchResponse:
    if isinstance(body, BayesianCurrentSingleRequest):
        from app.services.bayesian_noise_recommendations import create_noise_single

        return create_noise_single(request.app.state.settings, study_id, body)
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


@router.post(
    "/{study_id}/recommendation-batches",
    response_model=ScalarBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bayesian_recommendation_batch_route(
    request: Request,
    study_id: UUID,
    body: BayesianRecommendationBatchCreateRequest | BayesianCurrentBatchRequest,
) -> ScalarBatchResponse:
    return create_bayesian_recommendation_batch(
        request.app.state.settings,
        study_id,
        body,
    )


@router.get(
    "/{study_id}/recommendation-batches",
    response_model=BayesianAnyBatchListResponse,
)
def list_bayesian_recommendation_batches_route(
    request: Request,
    study_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> BayesianAnyBatchListResponse:
    return list_bayesian_recommendation_batches(
        request.app.state.settings,
        study_id,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{study_id}/recommendation-batches/latest",
    response_model=BayesianAnyLatestBatchResponse,
)
def get_latest_bayesian_recommendation_batch_route(
    request: Request,
    study_id: UUID,
) -> BayesianAnyLatestBatchResponse:
    return get_latest_bayesian_recommendation_batch(
        request.app.state.settings,
        study_id,
    )


@router.get(
    "/{study_id}/recommendation-batches/{batch_id}",
    response_model=BayesianAnyBatchResponse,
)
def get_bayesian_recommendation_batch_route(
    request: Request,
    study_id: UUID,
    batch_id: UUID,
) -> BayesianAnyBatchResponse:
    return get_bayesian_recommendation_batch(
        request.app.state.settings,
        study_id,
        batch_id,
    )
