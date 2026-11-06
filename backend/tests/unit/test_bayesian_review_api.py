from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from test_bayesian_batches_api import _batch_request, _completed_study

from app.core.config import Settings
from app.core.errors import ApiError
from app.main import create_app
from app.services.bayesian_review import MAX_REVIEWS, BayesianReviewStore
from app.statistics.bo_recommendation_core import calculate_noise_aware_batch


def _review_body(study):
    body = _batch_request(
        study["observation_history"]["history_revision_id"],
        batch_size=2,
        kind="expected_improvement",
    )
    body.update(
        schema_version=2,
        expected_history_sha256=study["observation_history"]["observation_history_sha256"],
    )
    body["search"]["batch_policy"] = "greedy_mc_joint_latent_improvement_v2"
    return body


def test_review_has_no_trials_and_confirmation_reuses_exact_calculation(tmp_path, monkeypatch):
    app = create_app(Settings(workspace_root=tmp_path))
    with TestClient(app) as client:
        study = _completed_study(client)
        base = f"/api/v1/bayesian-studies/{study['study_id']}"
        review = client.post(f"{base}/recommendation-reviews", json=_review_body(study))
        assert review.status_code == 200, review.json()
        preview = review.json()
        unchanged = client.get(base).json()
        assert unchanged["trials"] == study["trials"]
        assert unchanged["observation_history"] == study["observation_history"]
        assert client.get(f"{base}/recommendation-batches").json()["items"] == []

        def forbid_refit(*args, **kwargs):
            raise AssertionError("Confirmation must not refit")

        monkeypatch.setattr("app.services.bayesian_noise_recommendations._run_worker", forbid_refit)
        path = f"{base}/recommendation-reviews/{preview['review_id']}/confirm"
        request = {"expected_config_sha256": preview["config_sha256"]}
        confirmed = client.post(path, json=request)
        assert confirmed.status_code == 201, confirmed.json()
        batch = confirmed.json()
        assert batch["batch_id"] == preview["review_id"]
        for item, reviewed in zip(batch["items"], preview["calculation"]["items"], strict=True):
            for key, value in reviewed.items():
                assert item[key] == value
        repeated = client.post(path, json=request)
        assert repeated.status_code == 201, repeated.json()
        assert repeated.json() == batch
        assert client.get(base).json()["trial_count"] == study["trial_count"] + 2

    with TestClient(create_app(Settings(workspace_root=tmp_path))) as restarted:
        restored = restarted.post(path, json=request)
        assert restored.status_code == 201, restored.json()
        assert restored.json() == batch


@pytest.fixture
def review_client(tmp_path, monkeypatch):
    # Other tests exercise the owned spawn worker. These isolate source/CAS races.
    monkeypatch.setattr(
        "app.services.bayesian_noise_recommendations._run_worker",
        lambda payload, **kwargs: calculate_noise_aware_batch(payload),
    )
    app = create_app(Settings(workspace_root=tmp_path))
    with TestClient(app) as client:
        study = _completed_study(client)
        base = f"/api/v1/bayesian-studies/{study['study_id']}"
        response = client.post(f"{base}/recommendation-reviews", json=_review_body(study))
        assert response.status_code == 200, response.json()
        yield client, app, study, base, response.json()


def test_mismatch_and_tampered_confirmation_cannot_write(review_client):
    client, app, study, base, review = review_client
    path = f"{base}/recommendation-reviews/{review['review_id']}/confirm"
    assert client.post(path, json={"expected_config_sha256": "a" * 64}).status_code == 409
    assert (
        client.post(
            path, json={"expected_config_sha256": review["config_sha256"], "items": []}
        ).status_code
        == 422
    )
    assert client.get(base).json()["trials"] == study["trials"]
    wrong_study = _completed_study(client)
    wrong_path = path.replace(study["study_id"], wrong_study["study_id"])
    assert (
        client.post(
            wrong_path, json={"expected_config_sha256": review["config_sha256"]}
        ).status_code
        == 409
    )


def test_expired_review_is_not_a_pending_trial(review_client):
    client, app, study, base, review = review_client
    app.state.bayesian_reviews.clear()
    response = client.post(
        f"{base}/recommendation-reviews/{review['review_id']}/confirm",
        json={"expected_config_sha256": review["config_sha256"]},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "bayesian_review_expired"
    assert client.get(base).json()["trials"] == study["trials"]


def test_competing_batch_blocks_review_and_does_not_delete_committed_trials(review_client):
    client, app, study, base, review = review_client
    batch = client.post(f"{base}/recommendation-batches", json=_review_body(study))
    assert batch.status_code == 201, batch.json()
    # Preview and legacy direct-create route run the same current statistical core.
    for field in ("incumbent", "observation_view", "warnings", "limitations"):
        assert batch.json()[field] == review["calculation"][field]
    direct_model = batch.json()["shared_model"]
    reviewed_model = dict(review["calculation"]["shared_model"])
    # Independent fits preserve numbers, not measured wall-clock durations.
    assert direct_model.pop("fit_elapsed_ms") >= 0
    assert reviewed_model.pop("fit_elapsed_ms") >= 0
    assert direct_model == reviewed_model
    for saved, shown in zip(batch.json()["items"], review["calculation"]["items"], strict=True):
        assert all(saved[key] == value for key, value in shown.items())
    response = client.post(
        f"{base}/recommendation-reviews/{review['review_id']}/confirm",
        json={"expected_config_sha256": review["config_sha256"]},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "bayesian_optimization_pending_recommendation_exists"
    assert client.get(base).json()["trial_count"] == study["trial_count"] + 2
    # Once completed, the original review is stale rather than eligible again.
    history_id = study["observation_history"]["history_revision_id"]
    for item in batch.json()["items"]:
        done = client.put(
            f"{base}/trials/{item['trial']['trial_id']}/observation",
            json={"objective_value": 0.4, "expected_history_revision_id": history_id},
        )
        assert done.status_code == 200
        history_id = done.json()["observation_history"]["history_revision_id"]
    response = client.post(
        f"{base}/recommendation-reviews/{review['review_id']}/confirm",
        json={"expected_config_sha256": review["config_sha256"]},
    )
    assert response.json()["error"]["code"] == "bayesian_optimization_history_stale"


def test_concurrent_confirmations_commit_only_one_exact_batch(review_client, monkeypatch):
    client, app, study, base, review = review_client
    from app.services import bayesian_review

    original = bayesian_review.commit_noise_batch
    barrier = Barrier(2)

    def commit(*args, **kwargs):
        barrier.wait(timeout=10)
        return original(*args, **kwargs)

    monkeypatch.setattr(bayesian_review, "commit_noise_batch", commit)
    path = f"{base}/recommendation-reviews/{review['review_id']}/confirm"
    body = {"expected_config_sha256": review["config_sha256"]}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(client.post, path, json=body) for _ in range(2)]
        results = [future.result(timeout=30) for future in futures]
    assert [r.status_code for r in results] == [201, 201]
    assert results[0].json() == results[1].json()
    assert client.get(base).json()["trial_count"] == study["trial_count"] + 2


def test_review_store_bounded_immutable_expiring_and_single_fit(review_client):
    client, app, study, base, response = review_client
    body, review = app.state.bayesian_reviews.get(UUID(response["review_id"]))
    now = [0.0]
    store = BayesianReviewStore(clock=lambda: now[0])
    first = review.review_id
    store.put(body, review)
    copied_body, copied_review = store.get(first)
    copied_review.calculation.items.clear()
    assert len(store.get(first)[1].calculation.items) == 2
    for _ in range(MAX_REVIEWS):
        store.put(body, review.model_copy(update={"review_id": uuid4()}))
    with pytest.raises(ApiError, match="safely") as expired:
        store.get(first)
    assert expired.value.code == "bayesian_review_expired"
    store.put(body, review)
    now[0] = 1200
    with pytest.raises(ApiError):
        store.get(first)
    with store.calculation_slot():
        with pytest.raises(ApiError) as busy:
            with store.calculation_slot():
                pytest.fail("second fit admitted")
        assert busy.value.code == "bayesian_review_busy"
    with store.calculation_slot():
        pass


def test_review_rechecks_source_after_calculation(review_client, monkeypatch):
    client, app, study, base, review = review_client
    from app.services import bayesian_review

    original = bayesian_review.calculate_noise_recommendation

    def changed_source(*args, **kwargs):
        result = original(*args, **kwargs)
        response = client.post(
            f"{base}/recommendation-reviews/{review['review_id']}/confirm",
            json={"expected_config_sha256": review["config_sha256"]},
        )
        assert response.status_code == 201
        return result

    monkeypatch.setattr(bayesian_review, "calculate_noise_recommendation", changed_source)
    response = client.post(f"{base}/recommendation-reviews", json=_review_body(study))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "bayesian_optimization_pending_recommendation_exists"
    assert client.get(base).json()["trial_count"] == study["trial_count"] + 2


def test_review_memory_limit_rejects_without_keeping_payload(review_client, monkeypatch):
    client, app, study, base, response = review_client
    body, review = app.state.bayesian_reviews.get(UUID(response["review_id"]))
    store = BayesianReviewStore()
    monkeypatch.setattr("app.services.bayesian_review.MAX_REVIEW_BYTES", 1)
    with pytest.raises(ApiError) as error:
        store.put(body, review)
    assert error.value.code == "bayesian_review_size_exceeded"
    with pytest.raises(ApiError):
        store.get(review.review_id)


def test_confirmation_cache_eviction_race_replays_committed_batch(review_client, monkeypatch):
    client, app, study, base, review = review_client
    store = app.state.bayesian_reviews
    original = store.get
    path = f"{base}/recommendation-reviews/{review['review_id']}/confirm"
    request = {"expected_config_sha256": review["config_sha256"]}

    def interleaved_get(review_id):
        monkeypatch.setattr(store, "get", original)
        winner = client.post(path, json=request)
        assert winner.status_code == 201
        # The winner has discarded the memory entry after its successful commit.
        return original(review_id)

    monkeypatch.setattr(store, "get", interleaved_get)
    response = client.post(path, json=request)
    assert response.status_code == 201, response.json()
    assert response.json()["batch_id"] == review["review_id"]
    assert client.get(base).json()["trial_count"] == study["trial_count"] + 2


def test_replay_after_observations_returns_current_batch_without_new_trials(review_client):
    client, app, study, base, review = review_client
    path = f"{base}/recommendation-reviews/{review['review_id']}/confirm"
    request = {"expected_config_sha256": review["config_sha256"]}
    confirmed = client.post(path, json=request).json()
    first_trial = confirmed["items"][0]["trial"]["trial_id"]
    observed = client.put(
        f"{base}/trials/{first_trial}/observation",
        json={
            "objective_value": 1.25,
            "expected_history_revision_id": study["observation_history"]["history_revision_id"],
        },
    )
    assert observed.status_code == 200
    replay = client.post(path, json=request)
    assert replay.status_code == 201, replay.json()
    assert replay.json()["batch_state"] == "partially_completed"
    assert replay.json()["result_sha256"] == confirmed["result_sha256"]
    assert client.get(base).json()["trial_count"] == study["trial_count"] + 2
