"""Bounded local review of an ordered batch; confirmation never runs a fit."""

from collections import OrderedDict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import BoundedSemaphore, Lock
from time import monotonic
from uuid import UUID, uuid4

from app.api.v1.schemas.bayesian_noise import (
    BayesianNoiseBatchCreateRequest,
    BayesianNoiseBatchResponse,
)
from app.api.v1.schemas.bayesian_review import (
    BayesianRecommendationReviewConfirmRequest,
    BayesianRecommendationReviewResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.bayesian_noise_recommendations import (
    _error,
    _sha,
    calculate_noise_recommendation,
    commit_noise_batch,
    noise_config,
    validate_calculation,
    validated_noise_source,
)
from app.services.bayesian_recommendation_batches import get_bayesian_recommendation_batch
from app.storage.bayesian_studies import get_bayesian_recommendation_batch_record

REVIEW_TTL_SECONDS = 20 * 60
MAX_REVIEW_BYTES = 4 * 1024 * 1024
MAX_REVIEWS = 8


@dataclass(frozen=True)
class _ReviewEntry:
    request_json: str
    response_json: str
    deadline: float


class BayesianReviewStore:
    """Application-owned memory, not a workspace artifact or global singleton."""

    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._entries: OrderedDict[UUID, _ReviewEntry] = OrderedDict()
        self._lock = Lock()
        self._fit_slot = BoundedSemaphore(1)

    @contextmanager
    def calculation_slot(self) -> Iterator[None]:
        if not self._fit_slot.acquire(blocking=False):
            raise _error("bayesian_review_busy")
        try:
            yield
        finally:
            self._fit_slot.release()

    def put(
        self, body: BayesianNoiseBatchCreateRequest, review: BayesianRecommendationReviewResponse
    ) -> None:
        entry = _ReviewEntry(
            body.model_dump_json(), review.model_dump_json(), self._clock() + REVIEW_TTL_SECONDS
        )
        if len(entry.request_json.encode()) + len(entry.response_json.encode()) > MAX_REVIEW_BYTES:
            raise _error("bayesian_review_size_exceeded")
        with self._lock:
            self._prune()
            while len(self._entries) >= MAX_REVIEWS:
                self._entries.popitem(last=False)
            self._entries[review.review_id] = entry

    def get(
        self, review_id: UUID
    ) -> tuple[BayesianNoiseBatchCreateRequest, BayesianRecommendationReviewResponse]:
        with self._lock:
            self._prune()
            entry = self._entries.get(review_id)
        if entry is None:
            raise _error("bayesian_review_expired")
        return (
            BayesianNoiseBatchCreateRequest.model_validate_json(entry.request_json),
            BayesianRecommendationReviewResponse.model_validate_json(entry.response_json),
        )

    def discard(self, review_id: UUID) -> None:
        with self._lock:
            self._entries.pop(review_id, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _prune(self) -> None:
        now = self._clock()
        for key in [key for key, entry in self._entries.items() if entry.deadline <= now]:
            del self._entries[key]


def create_bayesian_review(
    settings: Settings,
    store: BayesianReviewStore,
    study_id: UUID,
    body: BayesianNoiseBatchCreateRequest,
) -> BayesianRecommendationReviewResponse:
    with store.calculation_slot():
        study, payload = validated_noise_source(settings, study_id, body)
        calculated = calculate_noise_recommendation(payload, body)
        # A source changed during fitting must not be presented as a current review.
        current, current_payload = validated_noise_source(settings, study_id, body)
        validate_calculation(calculated, current_payload, body)
    config_hash = _sha(noise_config(study, body))
    if config_hash != _sha(noise_config(current, body)):
        raise _error("bayesian_optimization_history_stale")
    review = BayesianRecommendationReviewResponse(
        review_id=uuid4(),
        study_id=study.study_id,
        study_version_id=study.study_version_id,
        source_history_revision_id=body.expected_history_revision_id,
        source_observation_history_sha256=body.expected_history_sha256,
        config_sha256=config_hash,
        expires_at=(datetime.now(timezone.utc) + timedelta(seconds=REVIEW_TTL_SECONDS)).isoformat(),
        calculation=calculated,
    )
    store.put(body, review)
    return review


def _committed_review(
    settings: Settings, study_id: UUID, review_id: UUID, expected_hash: str
) -> BayesianNoiseBatchResponse | None:
    record = get_bayesian_recommendation_batch_record(settings.workspace_root, str(review_id))
    if record is None:
        return None
    if record.config_sha256 != expected_hash or record.result_schema_version != 2:
        raise _error("bayesian_review_mismatch")
    result = get_bayesian_recommendation_batch(settings, study_id, review_id)
    if not isinstance(result, BayesianNoiseBatchResponse):
        raise _error("bayesian_review_mismatch")
    return result


def confirm_bayesian_review(
    settings: Settings,
    store: BayesianReviewStore,
    study_id: UUID,
    review_id: UUID,
    body: BayesianRecommendationReviewConfirmRequest,
) -> BayesianNoiseBatchResponse:
    existing = _committed_review(settings, study_id, review_id, body.expected_config_sha256)
    if existing is not None:
        return existing
    try:
        request, review = store.get(review_id)
        if review.study_id != study_id or review.config_sha256 != body.expected_config_sha256:
            raise _error("bayesian_review_mismatch")
        study, payload = validated_noise_source(settings, study_id, request)
        if _sha(noise_config(study, request)) != review.config_sha256:
            raise _error("bayesian_optimization_history_stale")
        validate_calculation(review.calculation, payload, request)
        commit_noise_batch(
            settings, study, request, review.calculation, reviewed_batch_id=review_id
        )
    except ApiError:
        # A concurrent confirmation may commit/discard between lookup and cache/source checks.
        replay = _committed_review(settings, study_id, review_id, body.expected_config_sha256)
        if replay is not None:
            return replay
        raise
    result = _committed_review(settings, study_id, review_id, body.expected_config_sha256)
    if result is None:
        raise _error()
    store.discard(review_id)
    return result
