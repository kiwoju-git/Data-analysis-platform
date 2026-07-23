from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict

from app.core.runtime_contract import API_CONTRACT_VERSION, RUNTIME_CAPABILITIES
from app.storage.metadata import SCHEMA_VERSION

APP_VERSION = "0.1.0"


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ready"]
    service: Literal["datalab-studio-api"]
    version: str


class RuntimeCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_management: bool
    dataset_version_metadata: bool
    dataset_version_deletion: bool
    dataset_version_archiving: bool
    dataset_version_cascade_deletion: bool
    dataset_version_preserve_unverified_cleanup: bool
    regression_model_metadata: bool
    regression_model_deletion: bool
    dedicated_predict: bool
    dedicated_response_optimizer: bool
    bayesian_optimization: bool


class RuntimeInfoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: Literal["datalab-studio-api"]
    app_version: str
    api_contract_version: int
    metadata_schema_version: int
    build_commit: str
    capabilities: RuntimeCapabilities


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    return HealthResponse(
        status="ready",
        service="datalab-studio-api",
        version=APP_VERSION,
    )


@router.get("/runtime-info", response_model=RuntimeInfoResponse)
def read_runtime_info(request: Request, response: Response) -> RuntimeInfoResponse:
    response.headers["Cache-Control"] = "no-store"
    return RuntimeInfoResponse(
        service="datalab-studio-api",
        app_version=APP_VERSION,
        api_contract_version=API_CONTRACT_VERSION,
        metadata_schema_version=SCHEMA_VERSION,
        build_commit=request.app.state.settings.git_commit or "unknown",
        capabilities=RuntimeCapabilities(**RUNTIME_CAPABILITIES),
    )
