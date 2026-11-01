"""Typed adapters from verified stored design/model contracts to domain regions."""

from app.api.v1.schemas.doe import ResponseSurfaceDesignResponse, RsmFinalBasisResponse
from app.statistics.rsm_coding import RsmFactorCoding
from app.statistics.rsm_region import (
    RsmRegionFactor,
    RsmRegionInput,
    RsmRegionMode,
    resolve_rsm_region,
)


def region_for_design(
    design: ResponseSurfaceDesignResponse,
    mode: RsmRegionMode,
    custom_bounds: dict[str, tuple[float, float]] | None = None,
    basis: RsmFinalBasisResponse | None = None,
) -> tuple[RsmRegionFactor, ...]:
    stored_coding = design.coding
    if basis is not None:
        if basis.factor_names != [factor.name for factor in design.factors]:
            raise ValueError("doe_rsm_region_coding_mismatch")
        stored_coding = basis.coding
    return resolve_rsm_region(
        [RsmRegionInput(f.name, f.low, f.high, f.domain_kind, f.step) for f in design.factors],
        alpha=design.options.alpha,
        coding=None
        if stored_coding is None
        else {name: RsmFactorCoding(**value.model_dump()) for name, value in stored_coding.items()},
        actual_runs=[run.factor_levels for run in design.runs],
        coded_runs=[run.coded_levels for run in design.runs],
        mode=mode,
        custom_bounds=custom_bounds,
    )
