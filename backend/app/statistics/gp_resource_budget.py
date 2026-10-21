from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from math import ceil

MEMORY_BUDGET_BYTES = 512 * 1024**2
PREDICTION_CHUNK_SIZE = 256


class GpResourceError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class GpResourceEstimate:
    profile: str
    row_limit: int
    n_rows: int
    fold_training_sizes: tuple[int, ...]
    kernel_parameter_counts: tuple[int, ...]
    final_refit_count: int
    optimizer_start_count: int
    total_training_cubic_units: int
    estimated_peak_bytes: int
    prediction_peak_bytes: int
    prediction_chunk_size: int
    prediction_chunk_count: int
    memory_budget_bytes: int = MEMORY_BUDGET_BYTES
    memory_enforcement: str = "admission_estimate_not_os_limit"
    estimate_version: str = "exact_gp_peak_v1"

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


def _integer(value: int, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise GpResourceError("gp_resource_options_invalid")
    return value


def estimate_gp_resources(
    *,
    profile: str,
    n_rows: int,
    fold_training_sizes: Sequence[int],
    kernel_parameter_counts: Sequence[int],
    optimizer_restarts: int,
    cv_optimizer_restarts: int,
    retained_candidate_count: int,
    prediction_query_count: int,
) -> GpResourceEstimate:
    if profile not in {"standard_exact", "extended_exact"}:
        raise GpResourceError("gp_resource_options_invalid")
    row_limit = 500 if profile == "standard_exact" else 2000
    _integer(n_rows, 2, 2**31 - 1)
    if n_rows > row_limit:
        raise GpResourceError("gp_usable_rows_limit")
    sizes = tuple(_integer(value, 2, n_rows) for value in fold_training_sizes)
    parameters = tuple(_integer(value, 1, 64) for value in kernel_parameter_counts)
    if not parameters or len(parameters) > 4 or len(sizes) > 200:
        raise GpResourceError("gp_resource_options_invalid")
    restarts = _integer(optimizer_restarts, 0, 16)
    cv_restarts = _integer(cv_optimizer_restarts, 0, 16)
    retained = _integer(retained_candidate_count, 0, len(parameters) - 1)
    queries = _integer(prediction_query_count, 0, 100_000)
    refits = 1 + retained
    starts = len(parameters) * len(sizes) * (1 + cv_restarts) + refits * (1 + restarts)
    if starts > 256:
        raise GpResourceError("gp_kernel_search_budget_exceeded")

    # Serial fits still hold kernel, factorization, inverse/gradient workspaces.
    # Three parameter-sized tensors cover mixed-kernel pieces and concatenation.
    matrix_bytes = 8 * n_rows * n_rows
    fit_bytes = matrix_bytes * (5 + 3 * max(parameters))
    retained_bytes = matrix_bytes * retained
    transfer_bytes = matrix_bytes * 2 + 8 * n_rows * 64
    prediction_bytes = 8 * n_rows * min(queries, PREDICTION_CHUNK_SIZE) * 3
    result_bytes = queries * 128 + len(parameters) * n_rows * 1024
    peak = 64 * 1024**2 + fit_bytes + retained_bytes + transfer_bytes
    peak += prediction_bytes + result_bytes
    if peak > MEMORY_BUDGET_BYTES:
        raise GpResourceError("gp_memory_budget_exceeded")
    cubic = len(parameters) * sum(size**3 for size in sizes) * (1 + cv_restarts)
    cubic += refits * n_rows**3 * (1 + restarts)
    return GpResourceEstimate(
        profile=profile,
        row_limit=row_limit,
        n_rows=n_rows,
        fold_training_sizes=sizes,
        kernel_parameter_counts=parameters,
        final_refit_count=refits,
        optimizer_start_count=starts,
        total_training_cubic_units=cubic,
        estimated_peak_bytes=peak,
        prediction_peak_bytes=prediction_bytes,
        prediction_chunk_size=PREDICTION_CHUNK_SIZE,
        prediction_chunk_count=ceil(queries / PREDICTION_CHUNK_SIZE),
    )
