from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Final, Literal, cast
from uuid import UUID, uuid4

from fastapi import status

from app.api.v1.schemas.doe import (
    DoeDesignResponseValue,
    DoeResponseRevisionCreateRequest,
    DoeResponseRevisionHistoryResponse,
    DoeResponseRevisionResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import canonical_json_bytes, utc_now
from app.storage.metadata import (
    ExperimentDesignRecord,
    ExperimentDesignVersionRecord,
    ExperimentResponseRevisionRecord,
    ExperimentResponseRevisionValueRecord,
    ExperimentRunRecord,
    ExperimentRunResponseRecord,
    abandon_experiment_response_revision_record,
    count_experiment_response_revision_records,
    get_current_experiment_response_revision_record,
    get_experiment_design_record,
    get_experiment_design_version_record,
    get_experiment_response_revision_record,
    insert_experiment_response_revision_records,
    list_experiment_response_revision_records,
    list_experiment_response_revision_value_records,
    list_experiment_run_records,
)

RESPONSE_REVISION_SCHEMA_VERSION: Final[Literal[1]] = 1
SUPPORTED_METHOD_IDS = {"doe.factorial_design", "doe.response_surface"}


@dataclass(frozen=True)
class ResponseRevisionDependency:
    revision: ExperimentResponseRevisionRecord
    runs: list[ExperimentRunRecord]
    response_records: list[ExperimentRunResponseRecord]


def create_response_revision(
    settings: Settings,
    design_id: UUID,
    body: DoeResponseRevisionCreateRequest,
    *,
    allow_analyzed: bool,
    require_explicit_supersedes: bool,
    duplicate_run_error_code: str = "doe_response_revision_run_order_duplicate",
    run_set_error_code: str = "doe_response_revision_run_set_mismatch",
) -> DoeResponseRevisionResponse:
    design, version, runs = _load_design(settings, design_id)
    if design.status == "analyzed" and not allow_analyzed:
        raise _error(
            "doe_design_already_analyzed",
            "이미 분석된 DOE 설계는 새 revision API로만 수정할 수 있습니다.",
        )
    response_name = body.response_name.strip()
    if not response_name:
        raise _error("doe_response_name_required", "반응 이름을 입력해야 합니다.")
    unit = None if body.unit is None else body.unit.strip() or None
    run_by_order = {run.run_order: run for run in runs}
    submitted: dict[int, float] = {}
    for item in body.values:
        if item.run_order in submitted:
            raise _error(
                duplicate_run_error_code,
                "같은 run_order에 반응값이 두 번 제출되었습니다.",
            )
        submitted[item.run_order] = float(item.value)
    if set(submitted) != set(run_by_order):
        raise _error(
            run_set_error_code,
            "새 revision은 현재 설계의 모든 run_order와 정확히 일치해야 합니다.",
        )

    current = get_current_experiment_response_revision_record(
        settings.workspace_root,
        version.design_version_id,
        response_name,
    )
    requested_supersedes = (
        None
        if body.supersedes_response_revision_id is None
        else str(body.supersedes_response_revision_id)
    )
    if current is None and requested_supersedes is not None:
        raise _error(
            "doe_response_revision_conflict",
            "새 response stream에는 supersedes revision을 지정할 수 없습니다.",
        )
    if current is not None and (
        (require_explicit_supersedes and requested_supersedes is None)
        or (
            requested_supersedes is not None
            and requested_supersedes != current.response_revision_id
        )
    ):
        raise _error(
            "doe_response_revision_conflict",
            "수정 기준 revision이 현재 revision과 일치하지 않습니다.",
        )

    ordered_values = [
        {"run_order": run_order, "value": submitted[run_order]} for run_order in sorted(submitted)
    ]
    response_sha256 = canonical_response_revision_sha256(
        design_version_id=version.design_version_id,
        response_name=response_name,
        unit=unit,
        values=ordered_values,
    )
    if current is not None and current.response_sha256 == response_sha256:
        raise _error(
            "doe_response_revision_conflict",
            "현재 revision과 동일한 내용으로 새 revision을 만들 수 없습니다.",
        )

    now = utc_now()
    response_revision_id = str(uuid4())
    revision = ExperimentResponseRevisionRecord(
        response_revision_id=response_revision_id,
        design_version_id=version.design_version_id,
        response_name=response_name,
        unit=unit,
        revision_number=1 if current is None else current.revision_number + 1,
        state="completed",
        schema_version=RESPONSE_REVISION_SCHEMA_VERSION,
        response_sha256=response_sha256,
        value_count=len(ordered_values),
        supersedes_response_revision_id=None if current is None else current.response_revision_id,
        created_at=now,
        closed_at=now,
    )
    revision_values = [
        ExperimentResponseRevisionValueRecord(
            response_revision_id=response_revision_id,
            run_id=run_by_order[run_order].run_id,
            run_order=run_order,
            response_value=submitted[run_order],
        )
        for run_order in sorted(submitted)
    ]
    current_records = [
        ExperimentRunResponseRecord(
            response_id=str(uuid4()),
            design_version_id=version.design_version_id,
            run_id=value.run_id,
            response_name=response_name,
            response_value=value.response_value,
            unit=unit,
            created_at=now,
            updated_at=now,
        )
        for value in revision_values
    ]
    insert_experiment_response_revision_records(
        settings.workspace_root,
        design_id=design.design_id,
        revision=revision,
        values=revision_values,
        current_records=current_records,
        updated_at=now,
    )
    return _revision_response(design, revision, revision_values, is_current=True)


def get_response_revision(
    settings: Settings,
    design_id: UUID,
    response_revision_id: UUID,
) -> DoeResponseRevisionResponse:
    design, version, _runs = _load_design(settings, design_id)
    revision = get_experiment_response_revision_record(
        settings.workspace_root, str(response_revision_id)
    )
    if revision is None or revision.design_version_id != version.design_version_id:
        raise _not_found()
    values = _validated_revision_values(settings, revision, expected_run_count=version.run_count)
    current = get_current_experiment_response_revision_record(
        settings.workspace_root,
        version.design_version_id,
        revision.response_name,
    )
    return _revision_response(
        design,
        revision,
        values,
        is_current=current is not None
        and current.response_revision_id == revision.response_revision_id,
    )


def list_response_revisions(
    settings: Settings,
    design_id: UUID,
    response_name: str,
    *,
    offset: int,
    limit: int,
) -> DoeResponseRevisionHistoryResponse:
    design, version, _runs = _load_design(settings, design_id)
    normalized_name = response_name.strip()
    if not normalized_name:
        raise _error("doe_response_name_required", "반응 이름을 입력해야 합니다.")
    records = list_experiment_response_revision_records(
        settings.workspace_root,
        version.design_version_id,
        normalized_name,
        offset=offset,
        limit=limit,
    )
    current = get_current_experiment_response_revision_record(
        settings.workspace_root,
        version.design_version_id,
        normalized_name,
    )
    return DoeResponseRevisionHistoryResponse(
        design_id=design_id,
        design_version_id=UUID(version.design_version_id),
        response_name=normalized_name,
        total=count_experiment_response_revision_records(
            settings.workspace_root, version.design_version_id, normalized_name
        ),
        offset=offset,
        limit=limit,
        items=[
            _revision_response(
                design,
                revision,
                _validated_revision_values(
                    settings, revision, expected_run_count=version.run_count
                ),
                is_current=current is not None
                and current.response_revision_id == revision.response_revision_id,
            )
            for revision in records
        ],
    )


def abandon_response_revision(
    settings: Settings,
    design_id: UUID,
    response_revision_id: UUID,
) -> DoeResponseRevisionResponse:
    before = get_response_revision(settings, design_id, response_revision_id)
    if before.state != "completed":
        raise _error(
            "doe_response_revision_already_closed",
            "이미 abandoned 상태인 revision은 다시 변경할 수 없습니다.",
        )
    if before.is_current:
        raise _error(
            "doe_response_revision_state_invalid",
            "현재 revision은 abandon할 수 없습니다. 먼저 새 completed revision을 만드세요.",
        )
    changed = abandon_experiment_response_revision_record(
        settings.workspace_root,
        str(response_revision_id),
        closed_at=utc_now(),
    )
    if not changed:
        raise _error(
            "doe_response_revision_state_invalid",
            "분석에서 사용한 revision은 abandon할 수 없습니다.",
        )
    return get_response_revision(settings, design_id, response_revision_id)


def load_response_revision_dependency(
    settings: Settings,
    *,
    design_version_id: UUID,
    response_name: str,
    response_revision_id: UUID | None,
) -> ResponseRevisionDependency:
    normalized_name = response_name.strip()
    revision = (
        get_current_experiment_response_revision_record(
            settings.workspace_root, str(design_version_id), normalized_name
        )
        if response_revision_id is None
        else get_experiment_response_revision_record(
            settings.workspace_root, str(response_revision_id)
        )
    )
    if revision is None:
        raise _error(
            "doe_response_revision_not_found",
            "분석할 completed response revision을 찾을 수 없습니다.",
        )
    if (
        revision.design_version_id != str(design_version_id)
        or revision.response_name != normalized_name
    ):
        raise _error(
            "doe_response_revision_dependency_mismatch",
            "선택한 response revision이 설계 또는 반응 이름과 일치하지 않습니다.",
        )
    if revision.state != "completed":
        raise _error(
            "doe_response_revision_state_invalid",
            "completed response revision만 분석할 수 있습니다.",
        )
    runs = list_experiment_run_records(settings.workspace_root, str(design_version_id))
    values = _validated_revision_values(settings, revision, expected_run_count=len(runs))
    records = [
        ExperimentRunResponseRecord(
            response_id=f"revision:{revision.response_revision_id}:{value.run_order}",
            design_version_id=revision.design_version_id,
            run_id=value.run_id,
            response_name=revision.response_name,
            response_value=value.response_value,
            unit=revision.unit,
            created_at=revision.created_at,
            updated_at=revision.closed_at or revision.created_at,
        )
        for value in values
    ]
    return ResponseRevisionDependency(revision=revision, runs=runs, response_records=records)


def canonical_response_revision_sha256(
    *,
    design_version_id: str,
    response_name: str,
    unit: str | None,
    values: list[dict[str, int | float]],
) -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            {
                "schema_version": RESPONSE_REVISION_SCHEMA_VERSION,
                "design_version_id": design_version_id,
                "response_name": response_name,
                "unit": unit,
                "values": values,
            }
        )
    ).hexdigest()


def _validated_revision_values(
    settings: Settings,
    revision: ExperimentResponseRevisionRecord,
    *,
    expected_run_count: int,
) -> list[ExperimentResponseRevisionValueRecord]:
    values = list_experiment_response_revision_value_records(
        settings.workspace_root, revision.response_revision_id
    )
    runs = list_experiment_run_records(settings.workspace_root, revision.design_version_id)
    run_ids = {run.run_id for run in runs}
    if (
        revision.schema_version != RESPONSE_REVISION_SCHEMA_VERSION
        or revision.state not in {"completed", "abandoned"}
        or len(values) != revision.value_count
        or len(values) != len(runs)
        or {value.run_id for value in values} != run_ids
        or [value.run_order for value in values] != [run.run_order for run in runs]
        or len(values) != expected_run_count
    ):
        raise _error(
            "doe_response_revision_dependency_mismatch",
            "response revision의 run dependency를 검증할 수 없습니다.",
        )
    actual_sha256 = canonical_response_revision_sha256(
        design_version_id=revision.design_version_id,
        response_name=revision.response_name,
        unit=revision.unit,
        values=[{"run_order": value.run_order, "value": value.response_value} for value in values],
    )
    if actual_sha256 != revision.response_sha256:
        raise _error(
            "doe_response_revision_checksum_mismatch",
            "response revision checksum을 검증할 수 없습니다.",
        )
    return values


def _revision_response(
    design: ExperimentDesignRecord,
    revision: ExperimentResponseRevisionRecord,
    values: list[ExperimentResponseRevisionValueRecord],
    *,
    is_current: bool,
) -> DoeResponseRevisionResponse:
    return DoeResponseRevisionResponse(
        response_revision_id=UUID(revision.response_revision_id),
        design_id=UUID(design.design_id),
        design_version_id=UUID(revision.design_version_id),
        response_revision_schema_version=RESPONSE_REVISION_SCHEMA_VERSION,
        response_revision_sha256=revision.response_sha256,
        response_name=revision.response_name,
        unit=revision.unit,
        revision_number=revision.revision_number,
        state=cast(Literal["completed", "abandoned"], revision.state),
        is_current=is_current,
        response_count=revision.value_count,
        supersedes_response_revision_id=(
            None
            if revision.supersedes_response_revision_id is None
            else UUID(revision.supersedes_response_revision_id)
        ),
        created_at=revision.created_at,
        closed_at=revision.closed_at,
        values=[
            DoeDesignResponseValue(run_order=value.run_order, value=value.response_value)
            for value in values
        ],
    )


def _load_design(
    settings: Settings,
    design_id: UUID,
) -> tuple[ExperimentDesignRecord, ExperimentDesignVersionRecord, list[ExperimentRunRecord]]:
    design = get_experiment_design_record(settings.workspace_root, str(design_id))
    if design is None or design.method_id not in SUPPORTED_METHOD_IDS:
        raise ApiError(
            code="doe_design_not_found",
            message="요청한 DOE 설계를 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    version = get_experiment_design_version_record(
        settings.workspace_root,
        design.design_id,
        design.current_version,
    )
    if version is None:
        raise _error(
            "doe_response_revision_dependency_mismatch",
            "DOE design version metadata를 검증할 수 없습니다.",
        )
    runs = list_experiment_run_records(settings.workspace_root, version.design_version_id)
    if len(runs) != version.run_count:
        raise _error(
            "doe_response_revision_dependency_mismatch",
            "DOE run metadata를 검증할 수 없습니다.",
        )
    return design, version, runs


def _not_found() -> ApiError:
    return ApiError(
        code="doe_response_revision_not_found",
        message="요청한 response revision을 찾을 수 없습니다.",
        status_code=status.HTTP_404_NOT_FOUND,
    )


def _error(code: str, message: str) -> ApiError:
    return ApiError(code=code, message=message, status_code=status.HTTP_409_CONFLICT)
