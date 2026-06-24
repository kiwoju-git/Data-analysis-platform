from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.root import router as root_router
from app.api.v1.analysis_methods import router as analysis_methods_router
from app.api.v1.analysis_runs import router as analysis_runs_router
from app.api.v1.datasets import router as datasets_router
from app.api.v1.datasets import version_router as dataset_versions_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.storage.metadata import initialize_metadata_store


def create_lifespan(settings: Settings) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.metadata_store = initialize_metadata_store(settings.workspace_root)
        yield

    return lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    app_settings = settings or get_settings()

    app = FastAPI(
        title="DataLab Studio API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=create_lifespan(app_settings),
    )
    app.state.settings = app_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["DELETE", "GET", "PATCH", "POST"],
        allow_headers=["Accept", "Content-Type", "X-Correlation-ID"],
    )

    register_exception_handlers(app)
    app.include_router(root_router)
    app.include_router(analysis_methods_router, prefix="/api/v1")
    app.include_router(analysis_runs_router, prefix="/api/v1")
    app.include_router(datasets_router, prefix="/api/v1")
    app.include_router(dataset_versions_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    return app


app = create_app()
