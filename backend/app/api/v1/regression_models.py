from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.api.v1.schemas.analyses import (
    RegressionModelCatalogResponse,
    RegressionModelDeleteRequest,
    RegressionModelDeleteResponse,
    RegressionModelDeletionPreflightResponse,
    RegressionModelDependentPredictionPage,
    RegressionModelManifestResponse,
    RegressionModelMetadataResponse,
    RegressionModelMetadataUpdateRequest,
    RegressionPredictionCsvExportResponse,
    RegressionPredictionPreflightRequest,
    RegressionPredictionPreflightResponse,
    RegressionPredictionRequest,
    RegressionPredictionResponse,
    RegressionPredictionRowsPageResponse,
)
from app.services.analysis_run_exports import create_regression_prediction_csv_export
from app.services.regression_models import (
    create_regression_predictions,
    get_regression_model_manifest,
    get_regression_prediction_preflight,
    get_regression_prediction_rows,
    list_regression_models,
    update_regression_model_metadata,
)
from app.services.workspace_asset_retention import (
    delete_stored_regression_model,
    get_regression_model_deletion_preflight,
    list_regression_model_dependent_predictions,
)

router = APIRouter(prefix="/regression-models", tags=["regression-models"])


@router.get("", response_model=RegressionModelCatalogResponse)
def list_regression_models_route(
    request: Request,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    source_dataset_version_id: UUID | None = None,
    source_analysis_id: UUID | None = None,
) -> RegressionModelCatalogResponse:
    return list_regression_models(
        settings=request.app.state.settings,
        offset=offset,
        limit=limit,
        source_dataset_version_id=source_dataset_version_id,
        source_analysis_id=source_analysis_id,
    )


@router.post(
    "/predictions/{prediction_id}/exports/csv",
    response_model=RegressionPredictionCsvExportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_regression_prediction_csv_export_route(
    request: Request,
    prediction_id: UUID,
) -> RegressionPredictionCsvExportResponse:
    return create_regression_prediction_csv_export(
        settings=request.app.state.settings,
        prediction_id=prediction_id,
    )


@router.get(
    "/predictions/{prediction_id}/rows",
    response_model=RegressionPredictionRowsPageResponse,
)
def get_regression_prediction_rows_route(
    request: Request,
    prediction_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> RegressionPredictionRowsPageResponse:
    return get_regression_prediction_rows(
        settings=request.app.state.settings,
        prediction_id=prediction_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{model_id}", response_model=RegressionModelManifestResponse)
def get_regression_model_route(
    request: Request,
    model_id: UUID,
) -> RegressionModelManifestResponse:
    return get_regression_model_manifest(
        settings=request.app.state.settings,
        model_id=model_id,
    )


@router.patch("/{model_id}/metadata", response_model=RegressionModelMetadataResponse)
def update_regression_model_metadata_route(
    request: Request,
    model_id: UUID,
    body: RegressionModelMetadataUpdateRequest,
) -> RegressionModelMetadataResponse:
    return update_regression_model_metadata(
        settings=request.app.state.settings,
        model_id=model_id,
        body=body,
    )


@router.get(
    "/{model_id}/deletion-preflight",
    response_model=RegressionModelDeletionPreflightResponse,
)
def get_regression_model_deletion_preflight_route(
    request: Request,
    model_id: UUID,
) -> RegressionModelDeletionPreflightResponse:
    return get_regression_model_deletion_preflight(
        settings=request.app.state.settings,
        model_id=model_id,
    )


@router.get(
    "/{model_id}/predictions",
    response_model=RegressionModelDependentPredictionPage,
)
def list_regression_model_dependent_predictions_route(
    request: Request,
    model_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> RegressionModelDependentPredictionPage:
    return list_regression_model_dependent_predictions(
        settings=request.app.state.settings,
        model_id=model_id,
        offset=offset,
        limit=limit,
    )


@router.delete("/{model_id}", response_model=RegressionModelDeleteResponse)
def delete_regression_model_route(
    request: Request,
    model_id: UUID,
    body: RegressionModelDeleteRequest,
) -> RegressionModelDeleteResponse:
    return delete_stored_regression_model(
        settings=request.app.state.settings,
        model_id=model_id,
        body=body,
    )


@router.post(
    "/{model_id}/prediction-preflight",
    response_model=RegressionPredictionPreflightResponse,
)
def get_regression_prediction_preflight_route(
    request: Request,
    model_id: UUID,
    body: RegressionPredictionPreflightRequest,
) -> RegressionPredictionPreflightResponse:
    return get_regression_prediction_preflight(
        settings=request.app.state.settings,
        model_id=model_id,
        dataset_version_id=body.dataset_version_id,
    )


@router.post("/{model_id}/predictions", response_model=RegressionPredictionResponse)
def create_regression_predictions_route(
    request: Request,
    model_id: UUID,
    body: RegressionPredictionRequest,
) -> RegressionPredictionResponse:
    return create_regression_predictions(
        settings=request.app.state.settings,
        model_id=model_id,
        body=body,
    )
