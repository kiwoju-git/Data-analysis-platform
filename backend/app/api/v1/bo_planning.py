"""Fitted planning sources and immutable candidate revisions within a BO study."""

from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.api.v1.schemas import bo_planning as dto
from app.api.v1.schemas.bo_augmentation import (
    AugmentationRequest,
    AugmentationSelectionResponse,
)
from app.api.v1.schemas.bo_augmentation_batch import AugmentationBatchResponse
from app.api.v1.schemas.bo_auto_strategy import AutoStrategyRequest, AutoStrategyView
from app.api.v1.schemas.bo_candidates_v2 import (
    CandidatePageV2,
    CandidateRevisionCreateRequestV2,
    CandidateSetListV2,
)
from app.api.v1.schemas.bo_loo import LooRequest, LooView
from app.api.v1.schemas.bo_planning_batch import PlanningBatchResponse
from app.api.v1.schemas.reports import ReportSourceDescriptor
from app.services import bo_candidates_v2 as candidates
from app.services import bo_planning as service
from app.services.bo_planning_batches import confirm_planning_selection, get_planning_batch

router = APIRouter(prefix="/bayesian-studies", tags=["bayesian-planning"])


@router.post(
    "/{study_id}/planning-models/{model_id}/auto-strategy", response_model=AutoStrategyView
)
def auto_strategy(
    request: Request, study_id: UUID, model_id: UUID, body: AutoStrategyRequest
) -> AutoStrategyView:
    from app.services.bo_auto_strategy import get_auto_strategy

    return get_auto_strategy(request.app.state.settings, study_id, model_id, body)


@router.post("/{study_id}/planning-models/{model_id}/loo", response_model=LooView)
def model_loo(request: Request, study_id: UUID, model_id: UUID, body: LooRequest) -> LooView:
    from app.services.bo_loo import get_loo_view

    return get_loo_view(request.app.state.settings, study_id, model_id, body)


@router.post(
    "/{study_id}/augmentations",
    response_model=AugmentationSelectionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_augmentation(
    request: Request, study_id: UUID, body: AugmentationRequest
) -> AugmentationSelectionResponse:
    from app.services.bo_augmentation import create_augmentation_selection

    return create_augmentation_selection(request.app.state.settings, study_id, body)


@router.get(
    "/{study_id}/augmentations/{selection_id}", response_model=AugmentationSelectionResponse
)
def get_augmentation(
    request: Request, study_id: UUID, selection_id: UUID
) -> AugmentationSelectionResponse:
    from app.services.bo_augmentation import get_augmentation_selection

    return get_augmentation_selection(request.app.state.settings, study_id, selection_id)


@router.post(
    "/{study_id}/augmentations/{selection_id}/confirm",
    response_model=AugmentationBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_augmentation(
    request: Request, study_id: UUID, selection_id: UUID, body: dto.PlanningConfirmRequest
) -> AugmentationBatchResponse:
    from app.services.bo_augmentation_batches import confirm_augmentation_selection

    return confirm_augmentation_selection(request.app.state.settings, study_id, selection_id, body)


@router.get("/{study_id}/augmentation-batches/{batch_id}", response_model=AugmentationBatchResponse)
def get_augmentation_batch(
    request: Request, study_id: UUID, batch_id: UUID
) -> AugmentationBatchResponse:
    from app.services.bo_augmentation_batches import get_augmentation_batch as read

    return read(request.app.state.settings, study_id, batch_id)


@router.get(
    "/{study_id}/augmentation-batches/{batch_id}/report-source",
    response_model=ReportSourceDescriptor,
)
def augmentation_report_source(
    request: Request, study_id: UUID, batch_id: UUID
) -> ReportSourceDescriptor:
    from app.services.bo_augmentation_batches import get_augmentation_batch as read
    from app.services.dedicated_report_sources import bayesian_batch_source_descriptor

    settings = request.app.state.settings
    read(settings, study_id, batch_id)
    return bayesian_batch_source_descriptor(settings, str(study_id), str(batch_id))


@router.post(
    "/{study_id}/planning-models",
    response_model=dto.PlanningModelDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_model(
    request: Request, study_id: UUID, body: dto.PlanningModelCreateRequest
) -> dto.PlanningModelDetail:
    return service.create_planning_model(request.app.state.settings, study_id, body)


@router.get("/{study_id}/planning-models", response_model=dto.PlanningModelList)
def list_models(request: Request, study_id: UUID) -> dto.PlanningModelList:
    return service.list_planning_models(request.app.state.settings, study_id)


@router.get("/{study_id}/planning-models/{model_id}", response_model=dto.PlanningModelDetail)
def get_model(request: Request, study_id: UUID, model_id: UUID) -> dto.PlanningModelDetail:
    return service.get_planning_model(request.app.state.settings, study_id, model_id)


@router.post(
    "/{study_id}/planning-models/{model_id}/evaluate", response_model=dto.PlanningEvaluationResponse
)
def evaluate_model(
    request: Request,
    study_id: UUID,
    model_id: UUID,
    body: dto.PlanningEvaluationRequest,
) -> dto.PlanningEvaluationResponse:
    return service.evaluate_planning_model(request.app.state.settings, study_id, model_id, body)


@router.post(
    "/{study_id}/candidate-revisions",
    response_model=dto.CandidatePage | CandidatePageV2,
    status_code=status.HTTP_201_CREATED,
)
def create_revision(
    request: Request,
    study_id: UUID,
    body: dto.CandidateRevisionCreateRequest | CandidateRevisionCreateRequestV2,
) -> dto.CandidatePage | CandidatePageV2:
    if isinstance(body, CandidateRevisionCreateRequestV2):
        return candidates.create_candidate_revision_v2(request.app.state.settings, study_id, body)
    return service.create_candidate_revision(request.app.state.settings, study_id, body)


@router.get("/{study_id}/candidate-sets", response_model=CandidateSetListV2)
def list_candidate_sets(request: Request, study_id: UUID) -> CandidateSetListV2:
    return candidates.list_candidate_sets_v2(request.app.state.settings, study_id)


@router.get(
    "/{study_id}/candidate-revisions/{revision_id}",
    response_model=dto.CandidatePage | CandidatePageV2,
)
def get_candidate_page(
    request: Request,
    study_id: UUID,
    revision_id: UUID,
    offset: int = Query(default=0, ge=0, le=10000),
    limit: int = Query(default=50, ge=1, le=100),
) -> dto.CandidatePage | CandidatePageV2:
    return candidates.candidate_page_any(
        request.app.state.settings, study_id, revision_id, offset=offset, limit=limit
    )


@router.post(
    "/{study_id}/planning-selections",
    response_model=dto.PlanningSelectionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_selection(
    request: Request, study_id: UUID, body: dto.PlanningSelectionCreateRequest
) -> dto.PlanningSelectionResponse:
    return service.create_planning_selection(request.app.state.settings, study_id, body)


@router.get("/{study_id}/planning-selections", response_model=dto.PlanningSelectionList)
def list_selections(request: Request, study_id: UUID) -> dto.PlanningSelectionList:
    return service.list_planning_selections(request.app.state.settings, study_id)


@router.get(
    "/{study_id}/planning-selections/{selection_id}", response_model=dto.PlanningSelectionResponse
)
def get_selection(
    request: Request, study_id: UUID, selection_id: UUID
) -> dto.PlanningSelectionResponse:
    return service.get_planning_selection(request.app.state.settings, study_id, selection_id)


@router.post(
    "/{study_id}/planning-selections/{selection_id}/confirm",
    response_model=PlanningBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_selection(
    request: Request,
    study_id: UUID,
    selection_id: UUID,
    body: dto.PlanningConfirmRequest,
) -> PlanningBatchResponse:
    return confirm_planning_selection(request.app.state.settings, study_id, selection_id, body)


@router.get("/{study_id}/planning-batches/{batch_id}", response_model=PlanningBatchResponse)
def get_batch(request: Request, study_id: UUID, batch_id: UUID) -> PlanningBatchResponse:
    return get_planning_batch(request.app.state.settings, study_id, batch_id)


@router.get(
    "/{study_id}/planning-batches/{batch_id}/report-source",
    response_model=ReportSourceDescriptor,
)
def get_batch_report_source(
    request: Request, study_id: UUID, batch_id: UUID
) -> ReportSourceDescriptor:
    from app.services.dedicated_report_sources import bayesian_batch_source_descriptor

    settings = request.app.state.settings
    get_planning_batch(settings, study_id, batch_id)
    return bayesian_batch_source_descriptor(settings, str(study_id), str(batch_id))
