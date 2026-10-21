import copy
import math

import pytest
from fastapi.testclient import TestClient
from test_bayesian_batches_api import _study_request

from app.api.v1.schemas.bayesian_noise import (
    BayesianNoiseBatchCreateRequest,
    BayesianNoiseCalculation,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.main import create_app
from app.services.analysis_run_execution import canonical_json_bytes
from app.services.bayesian_noise_recommendations import validate_calculation, worker_payload
from app.services.bayesian_studies import get_bayesian_study
from app.services.dedicated_report_sources import (
    list_dedicated_report_sources,
    prepare_dedicated_report_source,
)
from app.statistics.bo_observation_groups import prepare_bo_observation_view
from app.statistics.bo_recommendation_core import calculate_noise_aware_batch


def test_native_workflow_constraint_and_canonical_coordinates_roundtrip(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        definition = _study_request()
        definition.update(
            initial_design_seed=20260715,
            initial_design_policy="sha256_counter_uniform_feasible_v1",
            constraints=[
                {
                    "constraint_id": "constraint_1",
                    "name": "Synthetic limit",
                    "terms": [{"factor_id": "x", "coefficient": 1.0}],
                    "relation": "less_than_or_equal",
                    "bound": 0.75,
                }
            ],
        )
        created = client.post("/api/v1/bayesian-studies", json=definition)
        assert created.status_code == 201, created.json()
        study = created.json()
        history = study["observation_history"]["history_revision_id"]
        for trial, value in zip(study["trials"], [0.8, 1.0], strict=True):
            response = client.put(
                f"/api/v1/bayesian-studies/{study['study_id']}/trials/{trial['trial_id']}/observation",
                json={"objective_value": value, "expected_history_revision_id": history},
            )
            assert response.status_code == 200, response.json()
            history = response.json()["observation_history"]["history_revision_id"]
        typed_study = get_bayesian_study(settings, study["study_id"])
        before = canonical_json_bytes(typed_study.observation_history.model_dump(mode="json"))
        history_hash = typed_study.observation_history.observation_history_sha256
        request = BayesianNoiseBatchCreateRequest.model_validate(
            {
                "schema_version": 2,
                "expected_history_revision_id": history,
                "expected_history_sha256": history_hash,
                "acquisition": {"kind": "expected_improvement", "xi_standardized": 0.01},
                "search": {
                    "random_seed": 20260715,
                    "candidate_count_per_step": 256,
                    "local_start_count_per_step": 4,
                    "max_iterations_per_step": 100,
                    "max_evaluations_total": 32768,
                    "model_max_iterations": 50,
                    "model_max_evaluations": 200,
                    "hyperparameter_restart_count": 0,
                    "time_budget_ms": 60000,
                    "jitter": 1e-8,
                    "duplicate_tolerance": 1e-6,
                    "total_trial_budget": 5,
                    "batch_policy": "greedy_mc_joint_latent_improvement_v2",
                },
            }
        )
        payload = worker_payload(typed_study, request, typed_study.trials)
        untouched = copy.deepcopy(payload)
        calculation = BayesianNoiseCalculation.model_validate(calculate_noise_aware_batch(payload))
        assert payload == untouched
        view = prepare_bo_observation_view(payload["observations"], payload["factors"])
        latent_id = str(calculation.incumbent.latent_incumbent_trial_id)
        canonical = view.raw_x[view.trial_ids.index(latent_id)].tolist()
        stored = next(row for row in payload["observations"] if row["trial_id"] == latent_id)[
            "normalized_coordinates"
        ]["x"]
        assert calculation.incumbent.latent_incumbent_coordinates_normalized == canonical
        assert stored != canonical[0]
        assert abs(stored - canonical[0]) <= 4 * math.ulp(stored)
        validate_calculation(calculation, payload, request)
        tampered = calculation.model_copy(deep=True)
        tampered.incumbent.latent_incumbent_coordinates_normalized = [
            math.nextafter(canonical[0], 1.0)
        ]
        with pytest.raises(ApiError, match="safely created or restored"):
            validate_calculation(tampered, payload, request)

        # Keep the coordinate/novelty envelope internally consistent: only the
        # actual public constraint should reject this forged recommendation.
        tampered = calculation.model_copy(deep=True)
        tampered.items[0].actual_coordinates = {"x": 0.9}
        tampered.items[0].normalized_coordinates = {"x": 0.95}
        tampered.items[0].nearest_existing_distance = min(
            math.dist([0.95], old) for old in payload["excluded_normalized"]
        )
        with pytest.raises(ApiError, match="safely created or restored"):
            validate_calculation(tampered, payload, request)
        greater_than = copy.deepcopy(payload)
        greater_than["constraints"][0].update(relation="greater_than_or_equal", bound=0.95)
        with pytest.raises(ApiError, match="safely created or restored"):
            validate_calculation(calculation, greater_than, request)

        path = f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches"
        forged = calculation.model_copy(deep=True)
        forged.incumbent.latent_incumbent_coordinates_normalized = [
            math.nextafter(canonical[0], 1.0)
        ]
        with monkeypatch.context() as patch:
            patch.setattr(
                "app.services.bayesian_noise_recommendations._run_worker",
                lambda *args, **kwargs: forged.model_dump(mode="json"),
            )
            rejected = client.post(path, json=request.model_dump(mode="json"))
            assert rejected.status_code == 409
            assert rejected.json()["error"]["code"] == "bayesian_optimization_artifact_mismatch"
            assert client.get(path).json()["items"] == []
            assert (
                len(client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()["trials"])
                == 2
            )

        response = client.post(path, json=request.model_dump(mode="json"))
        assert response.status_code == 201, response.json()
        result = response.json()
        assert result["items"][0]["actual_coordinates"]["x"] <= 0.75 + 1e-10
        restored = client.get(f"{path}/{result['batch_id']}")
        assert restored.status_code == 200, restored.json()
        assert restored.json() == result
        final = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")
        assert final.status_code == 200, final.json()
        assert canonical_json_bytes(final.json()["observation_history"]) == before
        assert final.json()["trials"][:2] == [
            trial.model_dump(mode="json") for trial in typed_study.trials
        ]
        source = next(
            item.source
            for item in list_dedicated_report_sources(settings, "bayesian_history_revision").items
            if item.source.attachment.kind == "batch"
        )

        def forbidden(*args, **kwargs):
            raise AssertionError("Restoring a constrained report must not refit or recommend")

        monkeypatch.setattr(
            "app.statistics.bo_recommendation_core.calculate_noise_aware_batch", forbidden
        )
        report = prepare_dedicated_report_source(settings, source, "en")
        assert report.payload["attachment"]["batch_id"] == result["batch_id"]
        assert report.payload["attachment"]["result_sha256"] == result["result_sha256"]
        assert client.get(f"{path}/{result['batch_id']}").json() == result
