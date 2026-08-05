from typing import Final

API_CONTRACT_VERSION: Final = 10

RUNTIME_CAPABILITIES: Final[dict[str, bool]] = {
    "asset_management": True,
    "dataset_version_metadata": True,
    "dataset_version_deletion": True,
    "dataset_version_archiving": True,
    "dataset_version_cascade_deletion": True,
    "dataset_version_preserve_unverified_cleanup": True,
    "regression_model_metadata": True,
    "regression_model_deletion": True,
    "dedicated_predict": True,
    "dedicated_response_optimizer": True,
    "bayesian_optimization": True,
    "graph_builder_preview": True,
    "dataset_cell_correction": True,
    "lhs_design": True,
    "bayesian_lhs_initial_design": True,
    "bayesian_batch_recommendation": True,
    "bayesian_objective_goal_modes": True,
}
