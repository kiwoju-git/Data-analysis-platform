"""Renew an explicit legacy decision from its immutable original inputs, never UI defaults."""

from uuid import UUID

from app.api.v1.schemas.bo_augmentation import AUGMENTATION_REQUEST
from app.api.v1.schemas.bo_augmentation_renewal import (
    AugmentationRenewalLineage,
    AugmentationRenewalRequest,
    AugmentationRenewalResponse,
)
from app.core.config import Settings
from app.services.bayesian_noise_recommendations import _error
from app.services.bo_augmentation import (
    augmentation_requires_renewal,
    create_augmentation_selection,
    get_augmentation_selection,
)
from app.storage.bo_planning import get_augmentation_renewal


def renew_augmentation_selection(
    settings: Settings, study_id: UUID, selection_id: UUID, body: AugmentationRenewalRequest
) -> AugmentationRenewalResponse:
    original = get_augmentation_selection(settings, study_id, selection_id)
    if (
        original.config_sha256 != body.expected_config_sha256
        or original.result_sha256 != body.expected_result_sha256
    ):
        raise _error("bayesian_planning_selection_mismatch")
    if original.confirmed_batch_id is not None:
        raise _error("bayesian_augmentation_already_confirmed")
    if not augmentation_requires_renewal(original.calculation):
        raise _error("bayesian_augmentation_renewal_not_required")
    if body.request_id == original.request.request_id:
        raise _error("bayesian_planning_request_conflict")
    request = AUGMENTATION_REQUEST.validate_python(
        {**original.request.model_dump(mode="json"), "request_id": str(body.request_id)}
    )
    selected = create_augmentation_selection(
        settings,
        study_id,
        request,
        renewal={
            "original_selection_id": str(selection_id),
            "original_config_sha256": body.expected_config_sha256,
            "original_result_sha256": body.expected_result_sha256,
        },
    )
    lineage = get_augmentation_renewal(
        settings.workspace_root, str(selected.selection_id), str(selected.study_version_id)
    )
    if lineage is None:
        raise _error("bayesian_planning_artifact_invalid")
    return AugmentationRenewalResponse(
        selection=selected, lineage=AugmentationRenewalLineage.model_validate(lineage)
    )
