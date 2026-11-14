"""Opt-in persistent mixture planning endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.api.v1.schemas.bo_mixed_workflow import MixedEvaluationRequest, MixedModelCreateRequest
from app.api.v1.schemas.bo_mixture import (
    MixtureArtifactResponse,
    MixtureCandidateCreateRequest,
    MixtureSelectionCreateRequest,
    MixtureStudyCreateRequest,
    MixtureStudyResponse,
)
from app.api.v1.schemas.bo_planning import PlanningConfirmRequest
from app.api.v1.schemas.reports import ReportSourceDescriptor
from app.services import bo_mixture_workflow as service
from app.services.bo_mixture_studies import create_mixture_study

router = APIRouter(prefix="/bayesian-studies", tags=["bayesian-studies"])


@router.post("/mixture", response_model=MixtureStudyResponse, status_code=status.HTTP_201_CREATED)
def create_study(request: Request, body: MixtureStudyCreateRequest) -> MixtureStudyResponse:
    return create_mixture_study(request.app.state.settings, body)


@router.post(
    "/{study_id}/mixture-planning-models",
    response_model=MixtureArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_model(request: Request, study_id: UUID, body: MixedModelCreateRequest) -> dict[str, Any]:
    return service.create_mixture_model(request.app.state.settings, study_id, body)


@router.get("/{study_id}/mixture-planning-models", response_model=MixtureArtifactResponse)
def list_models(request: Request, study_id: UUID) -> dict[str, Any]:
    return service.list_mixture_models(request.app.state.settings, study_id)


@router.get(
    "/{study_id}/mixture-planning-models/{model_id}", response_model=MixtureArtifactResponse
)
def get_model(request: Request, study_id: UUID, model_id: UUID) -> dict[str, Any]:
    return service.get_mixture_model(request.app.state.settings, study_id, model_id)


@router.post(
    "/{study_id}/mixture-planning-models/{model_id}/evaluate",
    response_model=MixtureArtifactResponse,
)
def evaluate_model(
    request: Request, study_id: UUID, model_id: UUID, body: MixedEvaluationRequest
) -> dict[str, Any]:
    return service.evaluate_mixture_model(request.app.state.settings, study_id, model_id, body)


@router.post(
    "/{study_id}/mixture-candidate-revisions",
    response_model=MixtureArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_candidate(
    request: Request, study_id: UUID, body: MixtureCandidateCreateRequest
) -> dict[str, Any]:
    return service.create_mixture_candidate(request.app.state.settings, study_id, body)


@router.get(
    "/{study_id}/mixture-candidate-revisions/{revision_id}", response_model=MixtureArtifactResponse
)
def get_candidate(
    request: Request,
    study_id: UUID,
    revision_id: UUID,
    offset: int = Query(default=0, ge=0, le=10000),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    return service.get_mixture_candidate(
        request.app.state.settings, study_id, revision_id, offset=offset, limit=limit
    )


@router.post(
    "/{study_id}/mixture-selections",
    response_model=MixtureArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_selection(
    request: Request, study_id: UUID, body: MixtureSelectionCreateRequest
) -> dict[str, Any]:
    return service.create_mixture_selection(request.app.state.settings, study_id, body)


@router.get("/{study_id}/mixture-selections/{selection_id}", response_model=MixtureArtifactResponse)
def get_selection(request: Request, study_id: UUID, selection_id: UUID) -> dict[str, Any]:
    return service.get_mixture_selection(request.app.state.settings, study_id, selection_id)


@router.post(
    "/{study_id}/mixture-selections/{selection_id}/confirm",
    response_model=MixtureArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_selection(
    request: Request, study_id: UUID, selection_id: UUID, body: PlanningConfirmRequest
) -> dict[str, Any]:
    return service.confirm_mixture_selection(
        request.app.state.settings, study_id, selection_id, body
    )


@router.get(
    "/{study_id}/mixture-planning-batches/{batch_id}", response_model=MixtureArtifactResponse
)
def get_batch(request: Request, study_id: UUID, batch_id: UUID) -> dict[str, Any]:
    return service.get_mixture_batch(request.app.state.settings, study_id, batch_id)


@router.get(
    "/{study_id}/mixture-planning-batches/{batch_id}/report-source",
    response_model=ReportSourceDescriptor,
)
def get_batch_report_source(
    request: Request, study_id: UUID, batch_id: UUID
) -> ReportSourceDescriptor:
    from app.services.bo_mixture_report_source import read_mixture_bayesian
    from app.services.dedicated_report_sources import bayesian_batch_source_descriptor, invalid

    descriptor = bayesian_batch_source_descriptor(
        request.app.state.settings, str(study_id), str(batch_id)
    )
    if descriptor.source.kind != "bayesian_history_revision":
        raise invalid("report_source_kind_mismatch")
    read_mixture_bayesian(request.app.state.settings, descriptor.source)
    return descriptor
