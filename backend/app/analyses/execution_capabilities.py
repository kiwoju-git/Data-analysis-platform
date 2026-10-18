"""Audited display metadata; tests bind these entries to the enforcing limits."""

from app.api.v1.schemas.analyses import AnalysisResourceLimit


def method_resource_limits(method_id: str) -> list[AnalysisResourceLimit] | None:
    # Undeclared methods return null, not an empty list suggesting unlimited work.
    entries: dict[str, list[AnalysisResourceLimit]] = {
        "regression.gaussian_process": [
            AnalysisResourceLimit(name="max_predictors", value=12, unit="predictors"),
            AnalysisResourceLimit(name="max_usable_rows", value=500, unit="rows"),
            AnalysisResourceLimit(
                name="max_usable_rows", value=200, unit="rows", variant="leave_one_out"
            ),
            AnalysisResourceLimit(name="max_optimizer_starts", value=256, unit="starts"),
            AnalysisResourceLimit(
                name="max_optimizer_restarts", value=10, unit="restarts", variant="final_refit"
            ),
            AnalysisResourceLimit(
                name="max_optimizer_restarts", value=5, unit="restarts", variant="cross_validation"
            ),
            AnalysisResourceLimit(name="max_time_budget", value=600, unit="seconds"),
        ],
        "regression.partial_least_squares": [
            AnalysisResourceLimit(name="max_predictors", value=100, unit="predictors"),
            AnalysisResourceLimit(name="max_components", value=30, unit="components"),
            AnalysisResourceLimit(name="max_usable_rows", value=20_000, unit="rows"),
            AnalysisResourceLimit(
                name="max_usable_rows", value=500, unit="rows", variant="leave_one_out"
            ),
        ],
        "quality.two_variances": [
            AnalysisResourceLimit(name="max_usable_rows", value=20_000, unit="rows"),
            AnalysisResourceLimit(name="max_plot_points", value=500, unit="points_per_group"),
        ],
        "regression.linear_model": [
            AnalysisResourceLimit(
                name="max_time_budget", value=300, unit="seconds", variant="regularized"
            ),
            AnalysisResourceLimit(
                name="max_worker_slots", value=1, unit="workers", variant="regularized"
            ),
        ],
    }
    return entries.get(method_id)
