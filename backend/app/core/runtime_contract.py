from typing import Final

API_CONTRACT_VERSION: Final = 2

RUNTIME_CAPABILITIES: Final[dict[str, bool]] = {
    "asset_management": True,
    "dataset_version_metadata": True,
    "dataset_version_deletion": True,
    "regression_model_metadata": True,
    "regression_model_deletion": True,
    "dedicated_predict": True,
    "dedicated_response_optimizer": True,
    "bayesian_optimization": True,
}
