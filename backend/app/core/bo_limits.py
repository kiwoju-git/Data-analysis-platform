"""Shared bounds for BO histories, independent of query and optimizer budgets."""

from typing import Final

MAX_BAYESIAN_TRIALS: Final = 500
MAX_BO_RESPONSES: Final = 6
# Six bounded 500-row model states plus provenance; not an unbounded result pipe.
MAX_BO_PLANNING_BYTES: Final = 24 * 1024 * 1024
MAX_COMPLETED_OBSERVATIONS: Final = 500
MAX_HISTORY_REVISIONS: Final = MAX_COMPLETED_OBSERVATIONS + 1
MAX_BAYESIAN_REFERENCE_POINTS: Final = 2 * MAX_BAYESIAN_TRIALS
MAX_BO_SNAPSHOT_NODES: Final = MAX_COMPLETED_OBSERVATIONS**2 + 100 * MAX_COMPLETED_OBSERVATIONS
