"""App-owned bounded receipts: explicit save accepts no client-computed values."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from threading import BoundedSemaphore, Lock
from time import monotonic
from typing import Any
from uuid import UUID, uuid4

from app.api.v1.schemas.bo_views import ViewEvaluationReceipt, ViewPayload
from app.core.errors import ApiError
from app.storage.bo_planning import planning_json, planning_sha

TTL_SECONDS = 20 * 60
MAX_RECEIPTS = 8
MAX_RECEIPT_BYTES = 4 * 1024 * 1024


def view_error(code: str, status: int = 409) -> ApiError:
    return ApiError(code=code, message="The diagnostic view could not be used.", status_code=status)


class BoViewReceiptStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._calculation = BoundedSemaphore(1)
        self._items: dict[UUID, tuple[float, str]] = {}

    @contextmanager
    def calculation(self) -> Iterator[None]:
        if not self._calculation.acquire(blocking=False):
            raise view_error("bayesian_view_busy")
        try:
            yield
        finally:
            self._calculation.release()

    def put(self, request: dict[str, Any], payload: ViewPayload) -> ViewEvaluationReceipt:
        receipt = ViewEvaluationReceipt(
            receipt_id=uuid4(),
            request_sha256=planning_sha(request),
            view_sha256=planning_sha(payload.model_dump(mode="json")),
            payload=payload,
            expires_at=(datetime.now(timezone.utc) + timedelta(seconds=TTL_SECONDS)).isoformat(),
        )
        encoded = planning_json({"request": request, "receipt": receipt.model_dump(mode="json")})
        if len(encoded.encode("utf-8")) > MAX_RECEIPT_BYTES:
            raise view_error("bayesian_view_capacity_exceeded")
        with self._lock:
            self._purge()
            if len(self._items) >= MAX_RECEIPTS:
                self._items.pop(next(iter(self._items)))
            self._items[receipt.receipt_id] = (monotonic() + TTL_SECONDS, encoded)
        return receipt

    def get(self, receipt_id: UUID) -> tuple[dict[str, Any], ViewEvaluationReceipt]:
        with self._lock:
            self._purge()
            item = self._items.get(receipt_id)
            if item is None:
                raise view_error("bayesian_view_receipt_expired")
            document = json.loads(item[1])
        return document["request"], ViewEvaluationReceipt.model_validate(document["receipt"])

    def _purge(self) -> None:
        now = monotonic()
        for key in [key for key, item in self._items.items() if item[0] <= now]:
            del self._items[key]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
