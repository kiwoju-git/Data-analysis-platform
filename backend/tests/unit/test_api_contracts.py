from uuid import UUID, uuid4

from app.api.v1.schemas.common import JobReference, JobState


def test_job_state_values_are_stable() -> None:
    assert [state.value for state in JobState] == [
        "queued",
        "running",
        "succeeded",
        "failed",
        "cancel_requested",
        "cancelled",
    ]


def test_job_reference_serializes_uuid_and_state() -> None:
    job_id = uuid4()

    payload = JobReference(job_id=job_id, state=JobState.QUEUED).model_dump(mode="json")

    assert payload == {
        "job_id": str(job_id),
        "state": "queued",
    }
    assert UUID(payload["job_id"]) == job_id
