from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

APP_VERSION = "0.1.0"


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ready"]
    service: Literal["datalab-studio-api"]
    version: str


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    return HealthResponse(
        status="ready",
        service="datalab-studio-api",
        version=APP_VERSION,
    )
