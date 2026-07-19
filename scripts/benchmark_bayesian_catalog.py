from __future__ import annotations

import argparse
import gc
import json
import math
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any
from uuid import UUID

from app.api.v1.schemas.bayesian import (
    BayesianFactorRequest,
    BayesianObjectiveRequest,
    BayesianObservationCreateRequest,
    BayesianRecommendationCreateRequest,
    BayesianRecommendationSearchRequest,
    BayesianStudyCreateRequest,
)
from app.core.config import Settings
from app.services.bayesian_recommendations import create_bayesian_recommendation
from app.services.bayesian_studies import (
    complete_bayesian_trial,
    create_bayesian_study,
    get_bayesian_study,
    list_bayesian_studies,
)
from app.storage.metadata import initialize_metadata_store


PAGE_SIZE = 20
SMALL_INITIAL_TRIALS = 2
MEDIUM_COMPLETED_TRIALS = 20
LARGE_TOTAL_TRIALS = 100


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure checksum-validated Bayesian Study catalog paging."
    )
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 5:
        raise ValueError("--repetitions must be between 1 and 5")
    if sys.version_info[:2] != (3, 10):
        raise RuntimeError("The product benchmark requires CPython 3.10.x")

    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="datalab-bayesian-catalog-") as directory:
        settings = Settings(workspace_root=Path(directory))
        initialize_metadata_store(settings.workspace_root)
        cases: list[dict[str, Any]] = []

        _create_small_studies(settings, count=20, start_index=0)
        cases.append(
            _catalog_case(
                settings,
                study_count=20,
                first_page_profile="20 small Studies",
                repetitions=args.repetitions,
            )
        )

        _create_small_studies(settings, count=79, start_index=20)
        medium = _create_study(settings, index=99, initial_size=MEDIUM_COMPLETED_TRIALS)
        _complete_initial_trials(settings, medium.study_id)
        cases.append(
            _catalog_case(
                settings,
                study_count=100,
                first_page_profile="1 medium + 19 small Studies",
                repetitions=args.repetitions,
            )
        )

        _create_small_studies(settings, count=399, start_index=100)
        large = _create_study(settings, index=499, initial_size=64)
        _complete_initial_trials(settings, large.study_id)
        _extend_with_recommendations(settings, large.study_id, target_trial_count=100)
        cases.append(
            _catalog_case(
                settings,
                study_count=500,
                first_page_profile="1 large + 19 small Studies",
                repetitions=args.repetitions,
            )
        )

        large_restored = get_bayesian_study(settings, large.study_id)
        medium_restored = get_bayesian_study(settings, medium.study_id)

    print(
        json.dumps(
            {
                "benchmark_schema_version": 1,
                "commit_sha": _git_sha(),
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_only": True,
                "page_size": PAGE_SIZE,
                "repetitions": args.repetitions,
                "catalog_validation_policy": (
                    "every listed item uses the full checksum/dependency graph validator"
                ),
                "profiles": {
                    "small": {
                        "trial_count": 2,
                        "history_count": 1,
                        "recommendation_count": 0,
                    },
                    "medium": {
                        "trial_count": medium_restored.trial_count,
                        "history_count": medium_restored.completed_trial_count + 1,
                        "recommendation_count": 0,
                    },
                    "large": {
                        "trial_count": large_restored.trial_count,
                        "history_count": large_restored.completed_trial_count + 1,
                        "recommendation_count": (
                            large_restored.trial_count
                            - large_restored.initial_design.generated_size
                        ),
                    },
                },
                "cases": cases,
                "fixture_build_elapsed_seconds": round(
                    time.perf_counter() - started, 3
                ),
                "memory_policy": "tracemalloc Python allocation peak during each page call",
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _create_small_studies(settings: Settings, *, count: int, start_index: int) -> None:
    for index in range(start_index, start_index + count):
        _create_study(settings, index=index, initial_size=SMALL_INITIAL_TRIALS)


def _create_study(settings: Settings, *, index: int, initial_size: int):
    return create_bayesian_study(
        settings,
        BayesianStudyCreateRequest(
            name=f"Synthetic benchmark Study {index + 1}",
            factors=[
                BayesianFactorRequest(
                    factor_id="x",
                    name="Synthetic factor",
                    low=0.0,
                    high=1.0,
                    unit=None,
                )
            ],
            objective=BayesianObjectiveRequest(
                name="Synthetic objective",
                unit=None,
                direction="maximize",
                observation_policy="manual_single_observation",
            ),
            constraints=[],
            initial_design_seed=20260719 + index,
            initial_design_size=initial_size,
        ),
    )


def _complete_initial_trials(settings: Settings, study_id: UUID) -> None:
    study = get_bayesian_study(settings, study_id)
    history_id = study.observation_history.history_revision_id
    for trial in study.trials:
        transition = complete_bayesian_trial(
            settings,
            study_id,
            trial.trial_id,
            BayesianObservationCreateRequest(
                objective_value=_objective(trial.actual_coordinates["x"]),
                expected_history_revision_id=history_id,
            ),
        )
        history_id = transition.observation_history.history_revision_id


def _extend_with_recommendations(
    settings: Settings,
    study_id: UUID,
    *,
    target_trial_count: int,
) -> None:
    while True:
        study = get_bayesian_study(settings, study_id)
        if study.trial_count >= target_trial_count:
            return
        recommendation = create_bayesian_recommendation(
            settings,
            study_id,
            BayesianRecommendationCreateRequest(
                expected_history_revision_id=study.observation_history.history_revision_id,
                search=BayesianRecommendationSearchRequest(
                    random_seed=20260719 + study.trial_count,
                    candidate_count=64,
                    local_start_count=2,
                    max_iterations=40,
                    max_evaluations=512,
                    model_max_iterations=30,
                    model_max_evaluations=150,
                    time_budget_ms=15_000,
                    total_trial_budget=target_trial_count,
                ),
            ),
        )
        complete_bayesian_trial(
            settings,
            study_id,
            recommendation.trial.trial_id,
            BayesianObservationCreateRequest(
                objective_value=_objective(
                    recommendation.trial.actual_coordinates["x"]
                ),
                expected_history_revision_id=study.observation_history.history_revision_id,
            ),
        )


def _objective(value: float) -> float:
    return math.sin(3.0 * math.pi * value) - 0.2 * (value - 0.6) ** 2


def _catalog_case(
    settings: Settings,
    *,
    study_count: int,
    first_page_profile: str,
    repetitions: int,
) -> dict[str, Any]:
    middle_offset = ((study_count // 2) // PAGE_SIZE) * PAGE_SIZE
    return {
        "study_count": study_count,
        "first_page_profile": first_page_profile,
        "first_page": _measure_page(settings, offset=0, repetitions=repetitions),
        "middle_page": _measure_page(
            settings,
            offset=middle_offset,
            repetitions=repetitions,
        ),
    }


def _measure_page(
    settings: Settings,
    *,
    offset: int,
    repetitions: int,
) -> dict[str, Any]:
    elapsed_ms: list[float] = []
    peaks: list[int] = []
    returned = 0
    for _ in range(repetitions):
        gc.collect()
        tracemalloc.start()
        started = time.perf_counter()
        page = list_bayesian_studies(settings, offset=offset, limit=PAGE_SIZE)
        elapsed_ms.append((time.perf_counter() - started) * 1000.0)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peaks.append(peak)
        returned = len(page.items)
    return {
        "offset": offset,
        "returned": returned,
        "elapsed_ms": _summary(elapsed_ms),
        "python_peak_mib": _summary([item / (1024 * 1024) for item in peaks]),
    }


def _summary(values: list[float]) -> dict[str, float]:
    return {
        "minimum": round(min(values), 3),
        "median": round(statistics.median(values), 3),
        "maximum": round(max(values), 3),
    }


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


if __name__ == "__main__":
    raise SystemExit(main())
