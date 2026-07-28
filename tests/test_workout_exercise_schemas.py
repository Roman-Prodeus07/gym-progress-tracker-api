from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import (
    WorkoutExerciseCreate,
    WorkoutExerciseListResponse,
    WorkoutExerciseResponse,
    WorkoutExerciseUpdate,
)


def test_workout_exercise_create_normalizes_values() -> None:
    exercise_id = uuid4()

    workout_exercise = WorkoutExerciseCreate(
        exercise_id=exercise_id,
        rest_seconds=90,
        notes="  Controlled repetitions  ",
    )

    assert workout_exercise.exercise_id == exercise_id
    assert workout_exercise.position is None
    assert workout_exercise.rest_seconds == 90
    assert workout_exercise.notes == "Controlled repetitions"


def test_workout_exercise_create_rejects_explicit_null_position() -> None:
    with pytest.raises(ValidationError, match="Field cannot be null"):
        WorkoutExerciseCreate.model_validate(
            {
                "exercise_id": uuid4(),
                "position": None,
            }
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"exercise_id": None},
        {"position": None},
    ],
)
def test_workout_exercise_update_rejects_null_for_required_fields(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="Field cannot be null"):
        WorkoutExerciseUpdate.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"position": 0},
        {"rest_seconds": 0},
    ],
)
def test_workout_exercise_create_rejects_non_positive_values(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        WorkoutExerciseCreate.model_validate(
            {
                "exercise_id": uuid4(),
                **payload,
            }
        )


def test_workout_exercise_update_requires_at_least_one_field() -> None:
    with pytest.raises(
        ValidationError,
        match="At least one field must be provided",
    ):
        WorkoutExerciseUpdate()


def test_workout_exercise_update_allows_clearing_nullable_fields() -> None:
    update = WorkoutExerciseUpdate.model_validate(
        {
            "rest_seconds": None,
            "notes": None,
        }
    )

    assert update.rest_seconds is None
    assert update.notes is None
    assert update.model_fields_set == {"rest_seconds", "notes"}


def test_workout_exercise_response_excludes_internal_fields() -> None:
    now = datetime.now(UTC)
    workout_exercise_id = uuid4()
    workout_id = uuid4()
    exercise_id = uuid4()

    database_exercise = SimpleNamespace(
        id=exercise_id,
        name="Bench Press",
        slug="bench-press",
        description=None,
        primary_muscle_group="chest",
        equipment="barbell",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    database_workout_exercise = SimpleNamespace(
        id=workout_exercise_id,
        workout_session_id=workout_id,
        exercise_id=exercise_id,
        exercise=database_exercise,
        position=1,
        rest_seconds=90,
        notes=None,
        created_at=now,
        updated_at=now,
    )

    response = WorkoutExerciseResponse.model_validate(database_workout_exercise)
    response_data = response.model_dump()

    assert response_data["id"] == workout_exercise_id
    assert response_data["exercise_id"] == exercise_id
    assert response_data["exercise"]["name"] == "Bench Press"
    assert "workout_session_id" not in response_data
    assert "is_active" not in response_data["exercise"]


def test_workout_exercise_list_response_contains_pagination_metadata() -> None:
    now = datetime.now(UTC)
    exercise_id = uuid4()

    workout_exercise = WorkoutExerciseResponse(
        id=uuid4(),
        exercise_id=exercise_id,
        exercise={
            "id": exercise_id,
            "name": "Squat",
            "slug": "squat",
            "description": None,
            "primary_muscle_group": "quadriceps",
            "equipment": "barbell",
            "created_at": now,
            "updated_at": now,
        },
        position=1,
        rest_seconds=None,
        notes=None,
        created_at=now,
        updated_at=now,
    )

    response = WorkoutExerciseListResponse(
        items=[workout_exercise],
        total=1,
        limit=20,
        offset=0,
    )

    assert response.items == [workout_exercise]
    assert response.total == 1
    assert response.limit == 20
    assert response.offset == 0
