from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import (
    WorkoutSetCreate,
    WorkoutSetListResponse,
    WorkoutSetResponse,
    WorkoutSetUpdate,
)


def test_workout_set_create_normalizes_values() -> None:
    workout_set = WorkoutSetCreate(
        reps=8,
        weight_kg="80.500",
        rpe="8.5",
        notes="  Controlled repetitions  ",
    )

    assert workout_set.set_number is None
    assert workout_set.set_type == "working"
    assert workout_set.reps == 8
    assert workout_set.weight_kg == Decimal("80.500")
    assert workout_set.rpe == Decimal("8.5")
    assert workout_set.notes == "Controlled repetitions"


def test_workout_set_create_accepts_zero_reps() -> None:
    workout_set = WorkoutSetCreate(
        reps=0,
        set_type="failure",
    )

    assert workout_set.reps == 0
    assert workout_set.set_type == "failure"


def test_workout_set_create_rejects_explicit_null_set_number() -> None:
    with pytest.raises(ValidationError, match="Field cannot be null"):
        WorkoutSetCreate.model_validate(
            {
                "set_number": None,
                "reps": 8,
            }
        )


def test_workout_set_create_requires_performance_metric() -> None:
    with pytest.raises(
        ValidationError,
        match="At least one performance metric must be provided",
    ):
        WorkoutSetCreate(
            weight_kg="80.000",
            rpe="8.0",
        )


@pytest.mark.parametrize(
    "payload",
    [
        {
            "set_type": "invalid",
            "reps": 8,
        },
        {
            "set_number": 0,
            "reps": 8,
        },
        {
            "reps": -1,
        },
        {
            "reps": 8,
            "weight_kg": "-0.001",
        },
        {
            "duration_seconds": 0,
        },
        {
            "distance_meters": "0",
        },
        {
            "reps": 8,
            "rpe": "-0.1",
        },
        {
            "reps": 8,
            "rpe": "10.1",
        },
    ],
)
def test_workout_set_create_rejects_invalid_values(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        WorkoutSetCreate.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {
            "reps": 8,
            "weight_kg": "12345.678",
        },
        {
            "distance_meters": "12345678.12",
        },
        {
            "reps": 8,
            "rpe": "9.99",
        },
    ],
)
def test_workout_set_create_rejects_excessive_precision(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        WorkoutSetCreate.model_validate(payload)


def test_workout_set_update_requires_at_least_one_field() -> None:
    with pytest.raises(
        ValidationError,
        match="At least one field must be provided",
    ):
        WorkoutSetUpdate()


@pytest.mark.parametrize(
    "payload",
    [
        {"set_number": None},
        {"set_type": None},
    ],
)
def test_workout_set_update_rejects_null_for_required_fields(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="Field cannot be null"):
        WorkoutSetUpdate.model_validate(payload)


def test_workout_set_update_allows_clearing_nullable_fields() -> None:
    update = WorkoutSetUpdate.model_validate(
        {
            "weight_kg": None,
            "rpe": None,
            "notes": None,
        }
    )

    assert update.weight_kg is None
    assert update.rpe is None
    assert update.notes is None
    assert update.model_fields_set == {
        "weight_kg",
        "rpe",
        "notes",
    }


def test_workout_set_update_rejects_clearing_all_performance_metrics() -> None:
    with pytest.raises(
        ValidationError,
        match="At least one performance metric must be provided",
    ):
        WorkoutSetUpdate.model_validate(
            {
                "reps": None,
                "duration_seconds": None,
                "distance_meters": None,
            }
        )


def test_workout_set_response_excludes_parent_identifier() -> None:
    now = datetime.now(UTC)
    workout_set_id = uuid4()
    workout_exercise_id = uuid4()

    database_workout_set = SimpleNamespace(
        id=workout_set_id,
        workout_exercise_id=workout_exercise_id,
        set_number=1,
        set_type="working",
        reps=8,
        weight_kg=Decimal("80.000"),
        duration_seconds=None,
        distance_meters=None,
        rpe=Decimal("8.5"),
        notes=None,
        created_at=now,
        updated_at=now,
    )

    response = WorkoutSetResponse.model_validate(database_workout_set)
    response_data = response.model_dump()

    assert response_data["id"] == workout_set_id
    assert response_data["set_number"] == 1
    assert response_data["weight_kg"] == Decimal("80.000")
    assert "workout_exercise_id" not in response_data


def test_workout_set_list_response_contains_pagination_metadata() -> None:
    now = datetime.now(UTC)

    workout_set = WorkoutSetResponse(
        id=uuid4(),
        set_number=1,
        set_type="working",
        reps=8,
        weight_kg=Decimal("80.000"),
        duration_seconds=None,
        distance_meters=None,
        rpe=Decimal("8.0"),
        notes=None,
        created_at=now,
        updated_at=now,
    )

    response = WorkoutSetListResponse(
        items=[workout_set],
        total=1,
        limit=20,
        offset=0,
    )

    assert response.items == [workout_set]
    assert response.total == 1
    assert response.limit == 20
    assert response.offset == 0
