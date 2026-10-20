"""Product defaults for the explicitly supported unblocked full-cube CCD."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CcdCenterRecommendation:
    center_points: int | None
    reason: str
    factorial_runs: int
    axial_runs: int
    total_runs: int | None


def recommend_ccd_centers(
    factor_count: int,
    *,
    full_cube: bool = True,
    block_count: int = 1,
    factorial_replicates: int = 1,
    axial_replicates: int = 1,
) -> CcdCenterRecommendation:
    if not 2 <= factor_count <= 5:
        raise ValueError("doe_rsm_factor_count_out_of_range")
    cube, axial = 2**factor_count * factorial_replicates, 2 * factor_count * axial_replicates
    supported = full_cube and block_count == 1 and factorial_replicates == axial_replicates == 1
    count = {2: 5, 3: 6, 4: 7, 5: 10}[factor_count] if supported else None
    return CcdCenterRecommendation(
        count,
        "full_cube_unblocked_default" if supported else "custom_configuration",
        cube,
        axial,
        None if count is None else cube + axial + count,
    )
