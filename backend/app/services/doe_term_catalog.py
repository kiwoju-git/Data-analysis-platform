"""Design-owned catalog using the same term construction as final-model fitting."""

from uuid import UUID

from app.api.v1.schemas.doe_model_workflow import DoeAnalysisTerm, DoeAnalysisTermCatalog
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.doe_designs import get_factorial_design
from app.services.general_factorial_designs import get_general_factorial_design
from app.statistics.factorial_analysis import FactorialAnalysisRun, factorial_term_catalog
from app.statistics.general_factorial_analysis import (
    GeneralFactorialAnalysisRun,
    general_factorial_term_catalog,
)
from app.storage.metadata import get_experiment_design_record


def get_analysis_term_catalog(
    settings: Settings, design_id: UUID, max_interaction_order: int
) -> DoeAnalysisTermCatalog:
    record = get_experiment_design_record(settings.workspace_root, str(design_id))
    if record is None:
        raise ApiError(code="doe_design_not_found", message="Design not found.", status_code=404)
    if record.method_id == "doe.general_factorial_design":
        general = get_general_factorial_design(settings, design_id)
        order = max_interaction_order
        if not 1 <= order <= min(3, len(general.factors)):
            raise _invalid_order()
        runs = [
            GeneralFactorialAnalysisRun(
                run.run_order,
                run.level_indices,
                run.factor_levels,
                0.0,
            )
            for run in general.runs
        ]
        terms = general_factorial_term_catalog(
            runs,
            {factor.name: factor.levels for factor in general.factors},
            order,
        )
    elif record.method_id == "doe.factorial_design":
        design = get_factorial_design(settings, design_id)
        if design.fractional or design.screening:
            raise ApiError(
                code="doe_factorial_term_selection_unsupported_for_aliased_design",
                message="Manual term policies are available for full factorial designs only.",
            )
        order = max_interaction_order
        if not 1 <= order <= min(3, len(design.factors)):
            raise _invalid_order()
        calculation_runs = [
            FactorialAnalysisRun(
                run.run_order,
                run.standard_order,
                run.center_point,
                run.block_index,
                run.coded_levels,
                0.0,
            )
            for run in design.runs
        ]
        terms = factorial_term_catalog(calculation_runs, [f.name for f in design.factors], order)
    else:
        raise ApiError(
            code="doe_factorial_term_selection_design_unsupported",
            message="This design does not support factorial term selection.",
        )
    return DoeAnalysisTermCatalog(
        design_id=design_id,
        max_interaction_order=order,
        terms=[DoeAnalysisTerm.model_validate(term) for term in terms],
    )


def _invalid_order() -> ApiError:
    return ApiError(
        code="doe_factorial_interaction_order_invalid",
        message="Select an interaction order supported by the factor count.",
    )
