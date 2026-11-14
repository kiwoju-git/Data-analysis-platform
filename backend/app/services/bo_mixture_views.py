"""Bounded closure-preserving diagnostics of a validated saved mixture model."""

from time import monotonic
from typing import Any

from app.api.v1.schemas import bo_views as dto
from app.services import bo_planning
from app.services.bo_mixture_studies import MixtureValidatedStudy
from app.services.bo_view_receipts import view_error


def mixture_matrix(
    study: MixtureValidatedStudy,
    snapshot: dict[str, Any],
    source: dto.ViewSource,
    responses: list[dto.ViewResponse],
    body: dto.ProfilerMatrixRequest,
    started: float,
) -> dto.ProfilerMatrixPayload:
    try:
        study.design.canonical(body.holds)
    except ValueError:
        raise view_error("bayesian_view_holds_invalid", 422) from None
    axes = []
    for factor in study.factors:
        try:
            path = study.design.profile(body.holds, factor["factor_id"], count=body.points_per_axis)
        except ValueError:
            raise view_error("bayesian_view_holds_invalid", 422) from None
        points = path.pop("points")
        rows = []
        for offset in range(0, len(points), 100):
            budget = min(60000, int(body.time_budget_ms - (monotonic() - started) * 1000))
            if budget < 1000:
                raise view_error("bayesian_view_time_budget_exceeded")
            chunk = points[offset : offset + 100]
            raw = bo_planning._run(
                "mixture_evaluate",
                {
                    "snapshot": snapshot,
                    "points": chunk,
                    "time_budget_ms": budget,
                    "compute_acquisition": False,
                    "max_moment_evaluations": 65536,
                },
                time_budget_ms=budget,
            )
            if (monotonic() - started) * 1000 > body.time_budget_ms:
                raise view_error("bayesian_view_time_budget_exceeded")
            try:
                if len(raw) != len(chunk):
                    raise ValueError
                for expected, row in zip(chunk, raw, strict=True):
                    if (
                        row["input_coordinates"] != expected
                        or row["actual_coordinates"] != expected
                    ):
                        raise ValueError
                    rows.append(
                        dto.ProfilePoint.model_validate(
                            {key: row[key] for key in dto.ProfilePoint.model_fields}
                        )
                    )
            except (TypeError, ValueError, KeyError):
                raise view_error("bayesian_view_payload_invalid") from None
        kind = factor["domain_kind"]
        available = len(factor["levels"]) if kind in {"nominal", "ordinal"} else None
        if kind == "discrete_numeric":
            available = path.pop("available_level_count", None)
        axes.append(
            dto.ProfileAxis(
                factor_id=factor["factor_id"],
                name=factor["name"],
                unit=factor["unit"],
                kind=kind,
                available_level_count=available,
                points=rows,
                path=dto.ProfilePath.model_validate(path),
            )
        )
    return dto.ProfilerMatrixPayload(
        schema_version=2,
        kind="profiler_matrix",
        source=source,
        policy="source_locked_mixture_profiler_matrix_v1",
        mixture_domain=study.design.payload(),
        holds=body.holds,
        responses=responses,
        axes=axes,
        constraints=study.constraints,
        point_count=sum(len(axis.points) for axis in axes),
        warnings=snapshot["warnings"],
    )
