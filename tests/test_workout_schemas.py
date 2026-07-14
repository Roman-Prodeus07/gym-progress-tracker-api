from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import (
    WorkoutSessionCreate,
    WorkoutSessionListResponse,
    WorkoutSessionResponse,
    WorkoutSessionUpdate,
)


def test_workout_session_create_normalizes_strings() -> None:
    started_at = datetime.now(UTC)

    workout = WorkoutSessionCreate(
        name="  Push Day  ",
        notes="  Heavy chest session  ",
        started_at=started_at,
    )

    assert workout.name == "Push Day"
    assert workout.notes == "Heavy chest session"
    assert workout.started_at == started_at


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "   "},
        {
            "name": "Push Day",
            "started_at": datetime.now().replace(tzinfo=None),
        },
    ],
)
def test_workout_session_create_rejects_invalid_values(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        WorkoutSessionCreate.model_validate(payload)


def test_workout_session_update_requires_at_least_one_field() -> None:
    with pytest.raises(
        ValidationError,
        match="At least one field must be provided",
    ):
        WorkoutSessionUpdate()


@pytest.mark.parametrize(
    "payload",
    [
        {"name": None},
        {"started_at": None},
    ],
)
def test_workout_session_update_rejects_null_for_required_fields(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="Field cannot be null"):
        WorkoutSessionUpdate.model_validate(payload)


def test_workout_session_update_allows_clearing_nullable_fields() -> None:
    update = WorkoutSessionUpdate.model_validate(
        {
            "notes": None,
            "completed_at": None,
        }
    )

    assert update.notes is None
    assert update.completed_at is None
    assert update.model_fields_set == {"notes", "completed_at"}


def test_workout_session_update_rejects_invalid_time_range() -> None:
    started_at = datetime.now(UTC)
    completed_at = started_at - timedelta(minutes=1)

    with pytest.raises(
        ValidationError,
        match="completed_at cannot be earlier than started_at",
    ):
        WorkoutSessionUpdate(
            started_at=started_at,
            completed_at=completed_at,
        )


def test_workout_session_response_excludes_ownership_data() -> None:
    now = datetime.now(UTC)
    workout_id = uuid4()
    user_id = uuid4()

    database_workout = SimpleNamespace(
        id=workout_id,
        user_id=user_id,
        name="Push Day",
        notes=None,
        started_at=now,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )

    response = WorkoutSessionResponse.model_validate(database_workout)
    response_data = response.model_dump()

    assert response_data["id"] == workout_id
    assert response_data["name"] == "Push Day"
    assert "user_id" not in response_data


def test_workout_session_list_response_contains_pagination_metadata() -> None:
    now = datetime.now(UTC)
    workout = WorkoutSessionResponse(
        id=uuid4(),
        name="Pull Day",
        notes=None,
        started_at=now,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )

    response = WorkoutSessionListResponse(
        items=[workout],
        total=1,
        limit=20,
        offset=0,
    )

    assert response.total == 1
    assert response.limit == 20
    assert response.offset == 0
    assert response.items == [workout]
