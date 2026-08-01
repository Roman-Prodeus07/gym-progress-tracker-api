from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.schemas import WorkoutSessionDetailResponse


def test_workout_detail_serializes_nested_exercises_and_sets() -> None:
    now = datetime.now(UTC)
    workout_id = uuid4()
    workout_exercise_id = uuid4()
    exercise_id = uuid4()
    workout_set_id = uuid4()

    exercise = SimpleNamespace(
        id=exercise_id,
        name="Barbell Bench Press",
        slug="barbell-bench-press",
        description="Horizontal barbell press.",
        primary_muscle_group="chest",
        equipment="barbell",
        created_at=now,
        updated_at=now,
    )
    workout_set = SimpleNamespace(
        id=workout_set_id,
        workout_exercise_id=workout_exercise_id,
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
    workout_exercise = SimpleNamespace(
        id=workout_exercise_id,
        workout_session_id=workout_id,
        exercise_id=exercise_id,
        exercise=exercise,
        position=1,
        rest_seconds=120,
        notes="Controlled eccentric",
        workout_sets=[workout_set],
        created_at=now,
        updated_at=now,
    )
    workout = SimpleNamespace(
        id=workout_id,
        user_id=uuid4(),
        name="Push Day",
        notes=None,
        started_at=now,
        completed_at=now + timedelta(hours=1),
        workout_exercises=[workout_exercise],
        created_at=now,
        updated_at=now,
    )

    response = WorkoutSessionDetailResponse.model_validate(workout)
    response_data = response.model_dump(mode="json")

    assert response_data["id"] == str(workout_id)
    assert response_data["exercises"][0]["id"] == str(workout_exercise_id)
    assert response_data["exercises"][0]["exercise"]["id"] == str(exercise_id)
    assert response_data["exercises"][0]["sets"][0]["id"] == str(workout_set_id)
    assert response_data["exercises"][0]["sets"][0]["reps"] == 8

    assert "user_id" not in response_data
    assert "workout_exercises" not in response_data
    assert "workout_session_id" not in response_data["exercises"][0]
    assert "workout_sets" not in response_data["exercises"][0]
    assert "workout_exercise_id" not in response_data["exercises"][0]["sets"][0]


def test_workout_detail_serializes_empty_exercise_collection() -> None:
    now = datetime.now(UTC)
    workout = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        name="Empty Workout",
        notes=None,
        started_at=now,
        completed_at=now,
        workout_exercises=[],
        created_at=now,
        updated_at=now,
    )

    response = WorkoutSessionDetailResponse.model_validate(workout)

    assert response.exercises == []