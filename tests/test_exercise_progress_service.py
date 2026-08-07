from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.dialects import postgresql

import app.services.exercise_progress as exercise_progress_service
from app.schemas import ProgressDateRangeParams


def _candidate(
    *,
    workout_id: UUID,
    started_at: datetime,
    workout_set_id: UUID | None,
    set_type: str | None = "working",
    reps: int | None = 5,
    weight_kg: Decimal | None = Decimal("100.000"),
    duration_seconds: int | None = None,
    distance_meters: Decimal | None = None,
    rpe: Decimal | None = None,
    completed: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        workout_id=workout_id,
        started_at=started_at,
        completed_at=(started_at + timedelta(hours=1) if completed else None),
        workout_set_id=workout_set_id,
        set_type=set_type,
        reps=reps,
        weight_kg=weight_kg,
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        rpe=rpe,
    )


def test_build_exercise_progress_aggregates_strength_and_cardio_work_sets() -> None:
    exercise_id = uuid4()
    workout_id = uuid4()
    started_at = datetime(2026, 4, 1, 18, 0, tzinfo=UTC)
    first_set_id = uuid4()

    candidates = [
        _candidate(
            workout_id=workout_id,
            started_at=started_at,
            workout_set_id=first_set_id,
            reps=5,
            weight_kg=Decimal("100.000"),
            rpe=Decimal("8.0"),
        ),
        _candidate(
            workout_id=workout_id,
            started_at=started_at,
            workout_set_id=uuid4(),
            set_type="drop",
            reps=10,
            weight_kg=Decimal("80.000"),
            rpe=Decimal("9.0"),
        ),
        _candidate(
            workout_id=workout_id,
            started_at=started_at,
            workout_set_id=uuid4(),
            reps=None,
            weight_kg=None,
            duration_seconds=400,
            distance_meters=Decimal("1000.00"),
            rpe=Decimal("7.5"),
        ),
        _candidate(
            workout_id=workout_id,
            started_at=started_at,
            workout_set_id=uuid4(),
            set_type="failure",
            reps=None,
            weight_kg=None,
            duration_seconds=1500,
            distance_meters=Decimal("5000.00"),
            rpe=Decimal("8.5"),
        ),
        _candidate(
            workout_id=workout_id,
            started_at=started_at,
            workout_set_id=uuid4(),
            set_type="warmup",
            reps=20,
            weight_kg=Decimal("200.000"),
            duration_seconds=60,
            distance_meters=Decimal("10000.00"),
            rpe=Decimal("10.0"),
        ),
        _candidate(
            workout_id=workout_id,
            started_at=started_at,
            workout_set_id=first_set_id,
            reps=100,
            weight_kg=Decimal("999.000"),
            rpe=Decimal("10.0"),
        ),
        _candidate(
            workout_id=uuid4(),
            started_at=started_at,
            workout_set_id=uuid4(),
            reps=100,
            weight_kg=Decimal("999.000"),
            completed=False,
        ),
    ]
    query = ProgressDateRangeParams(
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 1),
    )

    progress = exercise_progress_service.build_exercise_progress(
        exercise_id,
        "Bench Press",
        candidates,
        query,
    )

    assert progress.exercise_id == exercise_id
    assert progress.exercise_name == "Bench Press"
    assert progress.period.model_dump() == {
        "date_from": date(2026, 4, 1),
        "date_to": date(2026, 4, 1),
        "timezone": "UTC",
    }
    assert len(progress.points) == 1

    point = progress.points[0]
    assert point.workout_id == workout_id
    assert point.started_at == started_at
    assert point.work_set_count == 4
    assert point.max_weight_kg == Decimal("100.000")
    assert point.max_reps == 10
    assert point.max_set_volume == Decimal("800.000")
    assert point.estimated_1rm_kg == Decimal("116.667")
    assert point.total_load_volume == Decimal("1300.000")
    assert point.max_distance_meters == Decimal("5000.00")
    assert point.total_distance_meters == Decimal("6000.00")
    assert point.longest_duration_seconds == 1500
    assert point.timed_set_duration_seconds == 1900
    assert point.best_pace_seconds_per_km == Decimal("300.000")
    assert point.average_rpe == Decimal("8.3")


def test_build_exercise_progress_keeps_completed_occurrence_without_sets() -> None:
    exercise_id = uuid4()
    workout_id = uuid4()
    query = ProgressDateRangeParams(
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 1),
    )
    candidate = _candidate(
        workout_id=workout_id,
        started_at=datetime(2026, 4, 1, 18, 0, tzinfo=UTC),
        workout_set_id=None,
        set_type=None,
        reps=None,
        weight_kg=None,
    )

    progress = exercise_progress_service.build_exercise_progress(
        exercise_id,
        "Pull-Up",
        [candidate],
        query,
    )

    point = progress.points[0]
    assert point.work_set_count == 0
    assert point.max_weight_kg is None
    assert point.max_reps is None
    assert point.max_set_volume is None
    assert point.estimated_1rm_kg is None
    assert point.total_load_volume == Decimal("0.000")
    assert point.max_distance_meters is None
    assert point.total_distance_meters == Decimal("0.00")
    assert point.longest_duration_seconds is None
    assert point.timed_set_duration_seconds == 0
    assert point.best_pace_seconds_per_km is None
    assert point.average_rpe is None


def test_build_exercise_progress_uses_local_date_and_orders_points() -> None:
    exercise_id = uuid4()
    first_workout_id = uuid4()
    second_workout_id = uuid4()
    excluded_workout_id = uuid4()
    query = ProgressDateRangeParams(
        date_from=date(2026, 3, 29),
        date_to=date(2026, 3, 29),
        timezone="Europe/London",
    )

    progress = exercise_progress_service.build_exercise_progress(
        exercise_id,
        "Treadmill Run",
        [
            _candidate(
                workout_id=second_workout_id,
                started_at=datetime(2026, 3, 29, 22, 30, tzinfo=UTC),
                workout_set_id=uuid4(),
            ),
            _candidate(
                workout_id=excluded_workout_id,
                started_at=datetime(2026, 3, 29, 23, 30, tzinfo=UTC),
                workout_set_id=uuid4(),
            ),
            _candidate(
                workout_id=first_workout_id,
                started_at=datetime(2026, 3, 29, 0, 30, tzinfo=UTC),
                workout_set_id=uuid4(),
            ),
        ],
        query,
    )

    assert [point.workout_id for point in progress.points] == [
        first_workout_id,
        second_workout_id,
    ]


@pytest.mark.anyio
async def test_get_exercise_progress_returns_none_for_unknown_exercise() -> None:
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=None),
        execute=AsyncMock(),
    )
    query = ProgressDateRangeParams(
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 1),
    )

    progress = await exercise_progress_service.get_exercise_progress(
        session,
        uuid4(),
        uuid4(),
        query,
    )

    assert progress is None
    session.execute.assert_not_awaited()


@pytest.mark.anyio
async def test_exercise_progress_query_is_owner_scoped_and_dst_aware() -> None:
    user_id = uuid4()
    exercise_id = uuid4()
    query_result = SimpleNamespace(all=Mock(return_value=[]))
    session = SimpleNamespace(
        scalar=AsyncMock(return_value="Bench Press"),
        execute=AsyncMock(return_value=query_result),
    )
    query = ProgressDateRangeParams(
        date_from=date(2026, 3, 29),
        date_to=date(2026, 3, 29),
        timezone="Europe/London",
    )

    progress = await exercise_progress_service.get_exercise_progress(
        session,
        user_id,
        exercise_id,
        query,
    )

    exercise_statement = session.scalar.await_args.args[0]
    compiled_exercise = exercise_statement.compile(dialect=postgresql.dialect())
    compiled_exercise_sql = " ".join(str(compiled_exercise).split())

    assert "FROM exercises" in compiled_exercise_sql
    assert "exercises.id =" in compiled_exercise_sql
    assert "exercises.is_active" not in compiled_exercise_sql
    assert exercise_id in compiled_exercise.params.values()

    statement = session.execute.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    compiled_sql = " ".join(str(compiled).split())

    assert "JOIN workout_exercises" in compiled_sql
    assert "LEFT OUTER JOIN workout_sets" in compiled_sql
    assert "workout_sessions.user_id =" in compiled_sql
    assert "workout_sessions.completed_at IS NOT NULL" in compiled_sql
    assert "workout_exercises.exercise_id =" in compiled_sql
    assert "workout_sessions.started_at >=" in compiled_sql
    assert "workout_sessions.started_at <" in compiled_sql
    assert user_id in compiled.params.values()
    assert exercise_id in compiled.params.values()
    assert datetime(2026, 3, 29, tzinfo=UTC) in compiled.params.values()
    assert datetime(2026, 3, 29, 23, 0, tzinfo=UTC) in compiled.params.values()

    assert progress is not None
    assert progress.exercise_name == "Bench Press"
    assert progress.points == []
