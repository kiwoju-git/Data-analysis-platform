from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.api.v1.health import APP_VERSION


class ApiLinks(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base: Literal["/api/v1"]
    health: Literal["/api/v1/health"]
    docs: Literal["/api/docs"]
    openapi: Literal["/api/openapi.json"]


class RootResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: Literal["datalab-studio-api"]
    version: str
    api: ApiLinks


router = APIRouter(tags=["root"])


@router.get("/", response_model=RootResponse, include_in_schema=False)
def read_root() -> RootResponse:
    return RootResponse(
        service="datalab-studio-api",
        version=APP_VERSION,
        api=ApiLinks(
            base="/api/v1",
            health="/api/v1/health",
            docs="/api/docs",
            openapi="/api/openapi.json",
        ),
    )
