from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.dialects import postgresql

import app.services.progress_summary as progress_summary_service
from app.schemas import ProgressBucket, ProgressSummaryQuery


def _candidate(
    *,
    workout_id: UUID,
    started_at: datetime,
    exercise_id: UUID | None,
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
        exercise_id=exercise_id,
        workout_set_id=workout_set_id,
        set_type=set_type,
        reps=reps,
        weight_kg=weight_kg,
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        rpe=rpe,
    )


def test_build_progress_summary_aggregates_local_buckets_and_work_sets() -> None:
    first_workout_id = uuid4()
    second_workout_id = uuid4()
    first_exercise_id = uuid4()
    second_exercise_id = uuid4()

    candidates = [
        _candidate(
            workout_id=first_workout_id,
            started_at=datetime(2026, 3, 29, 0, 30, tzinfo=UTC),
            exercise_id=first_exercise_id,
            workout_set_id=uuid4(),
            reps=5,
            weight_kg=Decimal("100.000"),
            duration_seconds=60,
            distance_meters=Decimal("1000.00"),
            rpe=Decimal("8.0"),
        ),
        _candidate(
            workout_id=first_workout_id,
            started_at=datetime(2026, 3, 29, 0, 30, tzinfo=UTC),
            exercise_id=first_exercise_id,
            workout_set_id=uuid4(),
            set_type="warmup",
            reps=10,
            weight_kg=Decimal("50.000"),
            duration_seconds=30,
            distance_meters=Decimal("200.00"),
            rpe=Decimal("10.0"),
        ),
        _candidate(
            workout_id=second_workout_id,
            started_at=datetime(2026, 3, 29, 23, 30, tzinfo=UTC),
            exercise_id=second_exercise_id,
            workout_set_id=uuid4(),
            set_type="drop",
            reps=10,
            weight_kg=Decimal("40.000"),
            duration_seconds=120,
            distance_meters=Decimal("500.00"),
            rpe=Decimal("9.0"),
        ),
        _candidate(
            workout_id=uuid4(),
            started_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
            exercise_id=uuid4(),
            workout_set_id=uuid4(),
            reps=100,
            weight_kg=Decimal("999.000"),
            completed=False,
        ),
        _candidate(
            workout_id=uuid4(),
            started_at=datetime(2026, 3, 28, 12, 0, tzinfo=UTC),
            exercise_id=uuid4(),
            workout_set_id=uuid4(),
        ),
    ]
    query = ProgressSummaryQuery(
        date_from=date(2026, 3, 29),
        date_to=date(2026, 3, 31),
        timezone="Europe/London",
        bucket=ProgressBucket.DAY,
    )

    summary = progress_summary_service.build_progress_summary(candidates, query)

    assert summary.period.model_dump() == {
        "date_from": date(2026, 3, 29),
        "date_to": date(2026, 3, 31),
        "timezone": "Europe/London",
        "bucket": ProgressBucket.DAY,
    }
    assert summary.totals.completed_workouts == 2
    assert summary.totals.active_days == 2
    assert summary.totals.unique_exercises == 2
    assert summary.totals.recorded_set_count == 3
    assert summary.totals.work_set_count == 2
    assert summary.totals.workout_duration_seconds == 7200
    assert summary.totals.timed_set_duration_seconds == 180
    assert summary.totals.total_distance_meters == Decimal("1500.00")
    assert summary.totals.total_load_volume == Decimal("900.000")
    assert summary.totals.average_rpe == Decimal("8.5")

    assert [bucket.bucket_start for bucket in summary.buckets] == [
        date(2026, 3, 29),
        date(2026, 3, 30),
        date(2026, 3, 31),
    ]
    assert summary.buckets[0].completed_workouts == 1
    assert summary.buckets[0].recorded_set_count == 2
    assert summary.buckets[0].work_set_count == 1
    assert summary.buckets[1].completed_workouts == 1
    assert summary.buckets[1].total_load_volume == Decimal("400.000")
    assert summary.buckets[2].completed_workouts == 0
    assert summary.buckets[2].total_distance_meters == Decimal("0.00")
    assert summary.buckets[2].total_load_volume == Decimal("0.000")
    assert summary.buckets[2].average_rpe is None


def test_build_progress_summary_counts_exercises_without_sets() -> None:
    query = ProgressSummaryQuery(
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 1),
    )
    candidate = _candidate(
        workout_id=uuid4(),
        started_at=datetime(2026, 4, 1, 18, 0, tzinfo=UTC),
        exercise_id=uuid4(),
        workout_set_id=None,
        set_type=None,
        reps=None,
        weight_kg=None,
    )

    summary = progress_summary_service.build_progress_summary([candidate], query)

    assert summary.totals.completed_workouts == 1
    assert summary.totals.unique_exercises == 1
    assert summary.totals.recorded_set_count == 0
    assert summary.totals.work_set_count == 0


def test_build_progress_summary_returns_zero_filled_week_buckets() -> None:
    query = ProgressSummaryQuery(
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 14),
        bucket=ProgressBucket.WEEK,
    )

    summary = progress_summary_service.build_progress_summary([], query)

    assert summary.totals.completed_workouts == 0
    assert [bucket.bucket_start for bucket in summary.buckets] == [
        date(2026, 3, 30),
        date(2026, 4, 6),
        date(2026, 4, 13),
    ]
    assert all(bucket.completed_workouts == 0 for bucket in summary.buckets)
    assert all(bucket.recorded_set_count == 0 for bucket in summary.buckets)
    assert all(bucket.average_rpe is None for bucket in summary.buckets)


@pytest.mark.anyio
async def test_summary_query_scopes_owner_completed_and_dst_range() -> None:
    user_id = uuid4()
    query_result = SimpleNamespace(all=Mock(return_value=[]))
    session = SimpleNamespace(
        execute=AsyncMock(return_value=query_result),
    )
    query = ProgressSummaryQuery(
        date_from=date(2026, 3, 29),
        date_to=date(2026, 3, 29),
        timezone="Europe/London",
        bucket=ProgressBucket.DAY,
    )

    summary = await progress_summary_service.get_progress_summary(
        session,
        user_id,
        query,
    )

    statement = session.execute.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    compiled_sql = " ".join(str(compiled).split())

    assert "workout_sessions.user_id =" in compiled_sql
    assert "workout_sessions.completed_at IS NOT NULL" in compiled_sql
    assert "workout_sessions.started_at >=" in compiled_sql
    assert "workout_sessions.started_at <" in compiled_sql
    assert "LEFT OUTER JOIN workout_exercises" in compiled_sql
    assert "LEFT OUTER JOIN workout_sets" in compiled_sql
    assert user_id in compiled.params.values()
    assert datetime(2026, 3, 29, tzinfo=UTC) in compiled.params.values()
    assert datetime(2026, 3, 29, 23, 0, tzinfo=UTC) in compiled.params.values()
    assert summary.totals.completed_workouts == 0
    assert len(summary.buckets) == 1
