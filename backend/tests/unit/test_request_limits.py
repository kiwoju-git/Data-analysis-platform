import asyncio
import io
import json
import tempfile
import threading

import pytest
from starlette.datastructures import Headers
from starlette.formparsers import MultiPartException
from starlette.requests import ClientDisconnect

from app.core.request_limits import (
    RequestBodyLimitMiddleware,
    _ClosingMultipartParser,
    _OwnedUploadFile,
)


def run_request(chunks, *, declared=None, limit=10, handle_error=False, path="/api/test"):
    received = []
    sent = []

    async def receive():
        chunk = chunks[len(received)]
        received.append(chunk)
        return {"type": "http.request", "body": chunk, "more_body": len(received) < len(chunks)}

    async def send(message):
        sent.append(message)

    async def app(scope, receive, send):
        try:
            while (await receive())["more_body"]:
                pass
        except Exception:
            if not handle_error:
                raise
            # FastAPI/Starlette may turn a parser exception into HTTP 400.
            await send({"type": "http.response.start", "status": 400, "headers": []})
            await send({"type": "http.response.body", "body": b"parser failure"})
            return
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"accepted"})

    headers = [(b"x-correlation-id", b"synthetic-request")]
    if declared is not None:
        headers.append((b"content-length", str(declared).encode()))
    scope = {"type": "http", "method": "POST", "path": path, "headers": headers}
    middleware = RequestBodyLimitMiddleware(
        app, max_request_bytes=limit, max_upload_request_bytes=7
    )
    asyncio.run(middleware(scope, receive, send))
    return received, sent


@pytest.mark.parametrize("declared", [None, 1, 10])
def test_actual_stream_size_not_declared_length(declared):
    received, sent = run_request([b"12345", b"67890", b"x", b"not-read"], declared=declared)
    assert len(received) == 3
    assert sent[0]["status"] == 413
    payload = json.loads(sent[1]["body"])
    assert payload["error"]["code"] == "request_body_too_large"
    assert payload["error"]["correlation_id"] == "synthetic-request"


def test_exact_limit_is_allowed():
    received, sent = run_request([b"12345", b"67890"])
    assert len(received) == 2
    assert sent[0]["status"] == 200


def test_declared_over_limit_is_rejected_before_reading():
    received, sent = run_request([b"not-read"], declared=11)
    assert not received
    assert sent[0]["status"] == 413


def test_parser_translation_does_not_hide_413():
    _, sent = run_request([b"12345678901"], handle_error=True)
    assert [message["status"] for message in sent if message["type"] == "http.response.start"] == [
        413
    ]
    assert b"parser failure" not in sent[1]["body"]


def test_upload_has_separate_whole_request_limit():
    _, sent = run_request([b"12345678"], path="/api/v1/datasets")
    assert sent[0]["status"] == 413
    _, sent = run_request([b"12345678"], path="/api/v1/datasets/paste")
    assert sent[0]["status"] == 200


@pytest.mark.parametrize("error", [ClientDisconnect, asyncio.CancelledError, OSError])
def test_disconnected_parser_closes_partial_spool(monkeypatch, error):
    files = []

    def spool(*args, **kwargs):
        file = tempfile.SpooledTemporaryFile(*args, **kwargs)
        files.append(file)
        return file

    monkeypatch.setattr("starlette.formparsers.SpooledTemporaryFile", spool)

    async def stream():
        yield (
            b'--boundary\r\nContent-Disposition: form-data; name="file"; '
            b'filename="x.csv"\r\n\r\na,b\n'
        )
        raise error()

    parser = _ClosingMultipartParser(
        Headers({"content-type": "multipart/form-data; boundary=boundary"}), stream(), max_files=1
    )
    with pytest.raises(error):
        asyncio.run(parser.parse())
    assert len(files) == 1 and files[0].closed


def test_cancelled_parser_waits_for_spool_write_before_closing(monkeypatch):
    started, release = threading.Event(), threading.Event()
    observed = []

    class SyntheticSpool(io.BytesIO):
        _max_size = 1
        _rolled = True

        def write(self, data):
            started.set()
            assert release.wait(10)
            observed.append(self.closed)
            return super().write(data)

    spool = SyntheticSpool()
    monkeypatch.setattr("starlette.formparsers.SpooledTemporaryFile", lambda **kwargs: spool)

    async def stream():
        yield (
            b'--b\r\nContent-Disposition: form-data; name="file"; '
            b'filename="x.csv"\r\n\r\nx\n1\r\n--b--\r\n'
        )

    parser = _ClosingMultipartParser(
        Headers({"content-type": "multipart/form-data; boundary=b"}), stream()
    )

    async def scenario():
        task = asyncio.create_task(parser.parse())
        try:
            assert await asyncio.to_thread(started.wait, 5)
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            assert not task.done()
            assert not spool.closed
        finally:
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert observed == [False]
    assert spool.closed


@pytest.mark.parametrize("method", ["seek", "close"])
def test_cancelled_spool_operation_finishes_before_returning(method):
    started, release = threading.Event(), threading.Event()
    completed = []

    class SyntheticSpool(io.BytesIO):
        _max_size = 1
        _rolled = True

        def seek(self, *args):
            if method == "seek":
                started.set()
                assert release.wait(10)
            result = super().seek(*args)
            completed.append("seek")
            return result

        def close(self):
            if method == "close":
                started.set()
                assert release.wait(10)
            super().close()
            completed.append("close")

    spool = SyntheticSpool(b"data")
    upload = _OwnedUploadFile(spool)

    async def scenario():
        task = asyncio.create_task(upload.seek(0) if method == "seek" else upload.close())
        try:
            assert await asyncio.to_thread(started.wait, 5)
            task.cancel()
            await asyncio.sleep(0)
            assert not task.done()
            assert not completed
        finally:
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert completed == [method]
    spool.close()


@pytest.mark.parametrize("suffix", [b"", b"\r\n--boundary\r\n"])
def test_truncated_multipart_closes_even_unlisted_spool(monkeypatch, suffix):
    files = []

    def spool(*args, **kwargs):
        file = tempfile.SpooledTemporaryFile(*args, **kwargs)
        files.append(file)
        return file

    monkeypatch.setattr("starlette.formparsers.SpooledTemporaryFile", spool)

    async def stream():
        yield (
            b'--boundary\r\nContent-Disposition: form-data; name="file"; '
            b'filename="x.csv"\r\n\r\na,b\n' + suffix
        )

    parser = _ClosingMultipartParser(
        Headers({"content-type": "multipart/form-data; boundary=boundary"}), stream(), max_files=1
    )
    with pytest.raises(MultiPartException, match="Incomplete multipart"):
        asyncio.run(parser.parse())
    assert len(files) == 1 and files[0].closed
