"""Streaming HTTP limits and the pinned Starlette multipart parsing boundary."""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.datastructures import FormData, UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.async_ownership import await_owned_io
from app.core.errors import ApiError, error_response, get_correlation_id


class RequestBodyLimitExceeded(MultiPartException):
    """Also lets Starlette close partially spooled multipart files on overflow."""


class _UploadFileLimitExceeded(MultiPartException):
    pass


class RequestBodyLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        max_request_bytes: int,
        max_upload_request_bytes: int,
    ) -> None:
        self.app = app
        self.max_request_bytes = max_request_bytes
        self.max_upload_request_bytes = min(max_upload_request_bytes, max_request_bytes)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        limit = (
            self.max_upload_request_bytes
            if scope["method"] == "POST" and scope["path"].rstrip("/") == "/api/v1/datasets"
            else self.max_request_bytes
        )
        response = error_response(
            "request_body_too_large",
            "The request body exceeds the configured byte limit.",
            get_correlation_id(request),
            413,
        )
        declared = request.headers.get("content-length")
        if declared is not None and declared.isdecimal() and int(declared) > limit:
            await response(scope, receive, send)
            return

        received = 0
        exceeded = False
        response_started = False
        rejection_sent = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    exceeded = True
                    raise RequestBodyLimitExceeded("Request body byte limit exceeded")
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal response_started, rejection_sent
            if exceeded:
                if response_started:
                    raise RuntimeError("Request limit exceeded after response start")
                if not rejection_sent:
                    rejection_sent = True
                    await response(scope, receive, send)
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except RequestBodyLimitExceeded:
            if response_started:
                raise
            if not rejection_sent:
                await response(scope, receive, send)


class _OwnedUploadFile(UploadFile):
    async def write(self, data: bytes) -> None:
        await await_owned_io(super().write(data))

    async def seek(self, offset: int) -> None:
        await await_owned_io(super().seek(offset))

    async def close(self) -> None:
        await await_owned_io(super().close())


class _ClosingMultipartParser(MultiPartParser):
    max_file_bytes = 100 * 1024 * 1024
    max_header_bytes = 16 * 1024
    _part_header_bytes = 0
    _part_file_bytes = 0
    _completed = False

    def on_end(self) -> None:
        self._completed = True
        super().on_end()

    def on_part_begin(self) -> None:
        self._part_header_bytes = 0
        self._part_file_bytes = 0
        super().on_part_begin()

    def _count_header(self, size: int) -> None:
        self._part_header_bytes += size
        if self._part_header_bytes > self.max_header_bytes:
            raise MultiPartException("Multipart headers exceeded maximum size")

    def on_header_field(self, data: bytes, start: int, end: int) -> None:
        self._count_header(end - start)
        super().on_header_field(data, start, end)

    def on_header_value(self, data: bytes, start: int, end: int) -> None:
        self._count_header(end - start)
        super().on_header_value(data, start, end)

    def on_part_data(self, data: bytes, start: int, end: int) -> None:
        if self._current_part.file is not None:
            self._part_file_bytes += end - start
            if self._part_file_bytes > self.max_file_bytes:
                raise _UploadFileLimitExceeded("Upload file byte limit exceeded")
        super().on_part_data(data, start, end)

    def on_headers_finished(self) -> None:
        super().on_headers_finished()
        file = self._current_part.file
        if file is not None:
            self._current_part.file = _OwnedUploadFile(
                file.file, size=file.size, filename=file.filename, headers=file.headers
            )

    async def parse(self) -> FormData:
        try:
            form = await super().parse()
            # python-multipart's finalize() does not validate the final boundary.
            if not self._completed:
                raise MultiPartException("Incomplete multipart body")
            return form
        except BaseException:
            # Starlette closes on parser/OSError failures; a disconnect or task
            # cancellation must also close every file already allocated by it.
            for file in self._files_to_close_on_error:
                file.close()
            raise


class LimitedDatasetUploadRoute(APIRoute):
    """Keep FastAPI's File schema/binding, but parse once with strict limits."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()
        if self.path.rstrip("/") not in {"/datasets", "/api/v1/datasets"} or self.methods != {
            "POST"
        }:
            return original

        async def limited_upload(request: Request) -> Response:
            settings = request.app.state.settings
            if (
                request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                != "multipart/form-data"
            ):
                raise ApiError(
                    "multipart_required", "Upload one file using multipart/form-data.", 415
                )
            parser = _ClosingMultipartParser(
                request.headers,
                request.stream(),
                max_files=1,
                max_fields=settings.max_multipart_fields,
                max_part_size=settings.max_multipart_field_bytes,
            )
            parser.max_file_bytes = settings.max_upload_bytes
            try:
                form = await parser.parse()
            except RequestBodyLimitExceeded:
                raise
            except _UploadFileLimitExceeded as error:
                raise ApiError(
                    "file_too_large", "The uploaded file exceeds the byte limit.", 413
                ) from error
            except MultiPartException as error:
                # These messages are owned by the pinned parser, never echoed.
                limit_error = error.message.startswith(
                    (
                        "Too many files.",
                        "Too many fields.",
                        "Part exceeded maximum size",
                        "Field exceeded maximum size",
                        "Multipart headers exceeded maximum size",
                    )
                )
                raise ApiError(
                    "multipart_limit_exceeded" if limit_error else "invalid_multipart",
                    "Multipart file count or field limits exceeded."
                    if limit_error
                    else "The multipart upload is invalid.",
                    413 if limit_error else 400,
                ) from error
            # FastAPI awaits request.form() again for typed File binding. Cache
            # the exact validated FormData, not a rebuilt body or a second parse.
            request._form = form
            try:
                return await original(request)
            finally:
                await form.close()

        return limited_upload
