import logging
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

LOGGER = logging.getLogger(__name__)


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    correlation_id: str
    developer_detail: str | None = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorBody


class ApiError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        developer_detail: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.developer_detail = developer_detail


def get_correlation_id(request: Request) -> str:
    header_value = request.headers.get("x-correlation-id")
    if header_value:
        return header_value[:128]
    return str(uuid4())


def error_response(
    code: str,
    message: str,
    correlation_id: str,
    status_code: int,
    developer_detail: str | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            correlation_id=correlation_id,
            developer_detail=developer_detail,
        ),
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        correlation_id = get_correlation_id(request)
        code = "not_found" if exc.status_code == status.HTTP_404_NOT_FOUND else "http_error"
        message = (
            "요청한 리소스를 찾을 수 없습니다."
            if exc.status_code == status.HTTP_404_NOT_FOUND
            else "요청을 처리하지 못했습니다."
        )
        LOGGER.info(
            "http_error code=%s correlation_id=%s path=%s status_code=%s",
            code,
            correlation_id,
            request.url.path,
            exc.status_code,
        )
        return error_response(
            code=code,
            message=message,
            correlation_id=correlation_id,
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        correlation_id = get_correlation_id(request)
        LOGGER.info(
            "validation_error correlation_id=%s path=%s error_count=%s",
            correlation_id,
            request.url.path,
            len(exc.errors()),
        )
        return error_response(
            code="validation_error",
            message="요청 형식이 올바르지 않습니다.",
            correlation_id=correlation_id,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        correlation_id = get_correlation_id(request)
        LOGGER.info(
            "api_error code=%s correlation_id=%s path=%s",
            exc.code,
            correlation_id,
            request.url.path,
        )
        return error_response(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
            status_code=exc.status_code,
            developer_detail=exc.developer_detail,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = get_correlation_id(request)
        LOGGER.exception(
            "unexpected_error correlation_id=%s path=%s error_type=%s",
            correlation_id,
            request.url.path,
            type(exc).__name__,
        )
        return error_response(
            code="internal_error",
            message="요청을 처리하지 못했습니다.",
            correlation_id=correlation_id,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
