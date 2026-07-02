from uuid import UUID

from fastapi import APIRouter, Request

from app.api.v1.schemas.analyses import (
    RegressionModelManifestResponse,
    RegressionPredictionPreflightRequest,
    RegressionPredictionPreflightResponse,
    RegressionPredictionRequest,
    RegressionPredictionResponse,
)
from app.services.regression_models import (
    create_regression_predictions,
    get_regression_model_manifest,
    get_regression_prediction_preflight,
)

router = APIRouter(prefix="/regression-models", tags=["regression-models"])


@router.get("/{model_id}", response_model=RegressionModelManifestResponse)
def get_regression_model_route(
    request: Request,
    model_id: UUID,
) -> RegressionModelManifestResponse:
    return get_regression_model_manifest(
        settings=request.app.state.settings,
        model_id=model_id,
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
