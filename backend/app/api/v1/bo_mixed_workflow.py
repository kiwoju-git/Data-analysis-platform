"""Explicit mixed-factor BO endpoints; existing numeric routes keep their contracts."""

from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.api.v1.schemas import bo_mixed_workflow as dto
from app.api.v1.schemas.bo_auto_strategy import AutoStrategyRequest, AutoStrategyView
from app.api.v1.schemas.bo_loo import LooRequest, LooView
from app.api.v1.schemas.bo_mixed_batch import MixedBatchResponse
from app.api.v1.schemas.bo_planning import PlanningConfirmRequest
from app.api.v1.schemas.reports import ReportSourceDescriptor
from app.services import bo_mixed_batches as batches
from app.services import bo_mixed_candidates as candidates
from app.services import bo_mixed_models as models
from app.services import bo_mixed_selections as selections

router = APIRouter(prefix="/bayesian-studies", tags=["bayesian-studies"])


@router.post(
    "/{study_id}/mixed-planning-models/{model_id}/auto-strategy", response_model=AutoStrategyView
)
def auto_strategy(
    request: Request, study_id: UUID, model_id: UUID, body: AutoStrategyRequest
) -> AutoStrategyView:
    from app.services.bo_auto_strategy import get_auto_strategy

    return get_auto_strategy(request.app.state.settings, study_id, model_id, body, mixed=True)


@router.post("/{study_id}/mixed-planning-models/{model_id}/loo", response_model=LooView)
def model_loo(request: Request, study_id: UUID, model_id: UUID, body: LooRequest) -> LooView:
    from app.services.bo_loo import get_loo_view

    return get_loo_view(request.app.state.settings, study_id, model_id, body, mixed=True)


@router.post(
    "/{study_id}/mixed-planning-models",
    response_model=dto.MixedModelDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_model(
    request: Request, study_id: UUID, body: dto.MixedModelCreateRequest
) -> dto.MixedModelDetail:
    return models.create_mixed_model(request.app.state.settings, study_id, body)


@router.get("/{study_id}/mixed-planning-models", response_model=dto.MixedModelList)
def list_models(request: Request, study_id: UUID) -> dto.MixedModelList:
    return models.list_mixed_models(request.app.state.settings, study_id)


@router.get("/{study_id}/mixed-planning-models/{model_id}", response_model=dto.MixedModelDetail)
def get_model(request: Request, study_id: UUID, model_id: UUID) -> dto.MixedModelDetail:
    return models.get_mixed_model(request.app.state.settings, study_id, model_id)


@router.post(
    "/{study_id}/mixed-planning-models/{model_id}/evaluate",
    response_model=dto.MixedEvaluationResponse,
)
def evaluate_model(
    request: Request, study_id: UUID, model_id: UUID, body: dto.MixedEvaluationRequest
) -> dto.MixedEvaluationResponse:
    return models.evaluate_mixed_model(request.app.state.settings, study_id, model_id, body)


@router.post(
    "/{study_id}/mixed-candidate-revisions",
    response_model=dto.MixedCandidatePage,
    status_code=status.HTTP_201_CREATED,
)
def create_candidate(
    request: Request, study_id: UUID, body: dto.MixedCandidateCreateRequest
) -> dto.MixedCandidatePage:
    return candidates.create_mixed_candidate(request.app.state.settings, study_id, body)


@router.get(
    "/{study_id}/mixed-candidate-revisions/{revision_id}", response_model=dto.MixedCandidatePage
)
def get_candidate(
    request: Request,
    study_id: UUID,
    revision_id: UUID,
    offset: int = Query(default=0, ge=0, le=10000),
    limit: int = Query(default=50, ge=1, le=100),
) -> dto.MixedCandidatePage:
    return candidates.mixed_candidate_page(
        request.app.state.settings, study_id, revision_id, offset=offset, limit=limit
    )


@router.get("/{study_id}/mixed-candidate-sets", response_model=dto.MixedCandidateList)
def list_candidates(request: Request, study_id: UUID) -> dto.MixedCandidateList:
    return candidates.list_mixed_candidates(request.app.state.settings, study_id)


@router.post(
    "/{study_id}/mixed-selections",
    response_model=dto.MixedSelectionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_selection(
    request: Request, study_id: UUID, body: dto.MixedSelectionInput
) -> dto.MixedSelectionResponse:
    return selections.create_mixed_selection(request.app.state.settings, study_id, body)


@router.get("/{study_id}/mixed-selections", response_model=dto.MixedSelectionList)
def list_selections(request: Request, study_id: UUID) -> dto.MixedSelectionList:
    return selections.list_mixed_selections(request.app.state.settings, study_id)


@router.get(
    "/{study_id}/mixed-selections/{selection_id}", response_model=dto.MixedSelectionResponse
)
def get_selection(
    request: Request, study_id: UUID, selection_id: UUID
) -> dto.MixedSelectionResponse:
    return selections.get_mixed_selection(request.app.state.settings, study_id, selection_id)


@router.post(
    "/{study_id}/mixed-selections/{selection_id}/confirm",
    response_model=MixedBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_selection(
    request: Request, study_id: UUID, selection_id: UUID, body: PlanningConfirmRequest
) -> MixedBatchResponse:
    return batches.confirm_mixed_selection(request.app.state.settings, study_id, selection_id, body)


@router.get("/{study_id}/mixed-planning-batches/{batch_id}", response_model=MixedBatchResponse)
def get_batch(request: Request, study_id: UUID, batch_id: UUID) -> MixedBatchResponse:
    return batches.get_mixed_batch(request.app.state.settings, study_id, batch_id)


@router.get(
    "/{study_id}/mixed-planning-batches/{batch_id}/report-source",
    response_model=ReportSourceDescriptor,
)
def get_batch_report_source(
    request: Request, study_id: UUID, batch_id: UUID
) -> ReportSourceDescriptor:
    from app.services.dedicated_report_sources import bayesian_batch_source_descriptor

    batches.get_mixed_batch(request.app.state.settings, study_id, batch_id)
    return bayesian_batch_source_descriptor(
        request.app.state.settings, str(study_id), str(batch_id)
    )
