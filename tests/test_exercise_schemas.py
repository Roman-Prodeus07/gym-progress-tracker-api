from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.schemas import ExerciseListResponse, ExerciseResponse


def test_exercise_response_exposes_safe_catalogue_fields() -> None:
    now = datetime.now(UTC)
    exercise_id = uuid4()

    database_exercise = SimpleNamespace(
        id=exercise_id,
        name="Bench Press",
        slug="bench-press",
        description="Barbell chest exercise.",
        primary_muscle_group="chest",
        equipment="barbell",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    response = ExerciseResponse.model_validate(database_exercise)
    response_data = response.model_dump()

    assert response_data["id"] == exercise_id
    assert response_data["name"] == "Bench Press"
    assert "is_active" not in response_data


def test_exercise_list_response_contains_pagination_metadata() -> None:
    now = datetime.now(UTC)
    exercise = ExerciseResponse(
        id=uuid4(),
        name="Squat",
        slug="squat",
        description=None,
        primary_muscle_group="quadriceps",
        equipment="barbell",
        created_at=now,
        updated_at=now,
    )

    response = ExerciseListResponse(
        items=[exercise],
        total=1,
        limit=20,
        offset=0,
    )

    assert response.items == [exercise]
    assert response.total == 1
    assert response.limit == 20
    assert response.offset == 0
