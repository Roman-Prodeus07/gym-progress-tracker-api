from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.progress import (
    MAX_PROGRESS_RANGE_DAYS,
    ExerciseProgressPointResponse,
    ExerciseProgressResponse,
    PersonalRecordListResponse,
    PersonalRecordResponse,
    PersonalRecordType,
    ProgressAggregateResponse,
    ProgressBucket,
    ProgressBucketResponse,
    ProgressDateRangeParams,
    ProgressPeriodResponse,
    ProgressSummaryPeriodResponse,
    ProgressSummaryQuery,
    ProgressSummaryResponse,
)


def test_progress_date_range_normalizes_timezone() -> None:
    params = ProgressDateRangeParams(
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
        timezone="  Europe/London  ",
    )

    assert params.date_from == date(2026, 1, 1)
    assert params.date_to == date(2026, 1, 31)
    assert params.timezone == "Europe/London"


def test_progress_summary_query_uses_contract_defaults() -> None:
    query = ProgressSummaryQuery(
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    )

    assert query.timezone == "UTC"
    assert query.bucket is ProgressBucket.WEEK


def test_progress_date_range_accepts_366_inclusive_days() -> None:
    params = ProgressDateRangeParams(
        date_from=date(2024, 1, 1),
        date_to=date(2024, 12, 31),
    )

    inclusive_days = (params.date_to - params.date_from).days + 1

    assert inclusive_days == MAX_PROGRESS_RANGE_DAYS


def test_progress_date_range_rejects_more_than_366_days() -> None:
    with pytest.raises(
        ValidationError,
        match="Date range cannot exceed 366 days",
    ):
        ProgressDateRangeParams(
            date_from=date(2024, 1, 1),
            date_to=date(2025, 1, 1),
        )


def test_progress_date_range_rejects_reversed_dates() -> None:
    with pytest.raises(
        ValidationError,
        match="date_from cannot be later than date_to",
    ):
        ProgressDateRangeParams(
            date_from=date(2026, 2, 1),
            date_to=date(2026, 1, 31),
        )


@pytest.mark.parametrize(
    "timezone_name",
    [
        "",
        "Not/A_Timezone",
        "../UTC",
    ],
)
def test_progress_date_range_rejects_invalid_timezone(
    timezone_name: str,
) -> None:
    with pytest.raises(
        ValidationError,
        match="timezone must be a valid IANA timezone",
    ):
        ProgressDateRangeParams(
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
            timezone=timezone_name,
        )


def build_progress_aggregate() -> ProgressAggregateResponse:
    return ProgressAggregateResponse(
        completed_workouts=3,
        active_days=2,
        unique_exercises=4,
        recorded_set_count=18,
        work_set_count=15,
        workout_duration_seconds=7200,
        timed_set_duration_seconds=600,
        total_distance_meters=Decimal("1500.00"),
        total_load_volume=Decimal("12345.500"),
        average_rpe=Decimal("8.3"),
    )


def test_progress_summary_response_serializes_decimal_contract() -> None:
    totals = build_progress_aggregate()
    bucket = ProgressBucketResponse(
        bucket_start=date(2026, 1, 5),
        **totals.model_dump(),
    )

    response = ProgressSummaryResponse(
        period=ProgressSummaryPeriodResponse(
            date_from=date(2026, 1, 5),
            date_to=date(2026, 1, 11),
            timezone="Europe/London",
            bucket=ProgressBucket.WEEK,
        ),
        totals=totals,
        buckets=[bucket],
    )

    response_data = response.model_dump(mode="json")

    assert response_data["period"] == {
        "date_from": "2026-01-05",
        "date_to": "2026-01-11",
        "timezone": "Europe/London",
        "bucket": "week",
    }
    assert response_data["totals"]["total_load_volume"] == "12345.500"
    assert response_data["totals"]["total_distance_meters"] == "1500.00"
    assert response_data["totals"]["average_rpe"] == "8.3"
    assert response_data["buckets"][0]["bucket_start"] == "2026-01-05"


def test_progress_aggregate_supports_zero_filled_bucket() -> None:
    aggregate = ProgressAggregateResponse(
        completed_workouts=0,
        active_days=0,
        unique_exercises=0,
        recorded_set_count=0,
        work_set_count=0,
        workout_duration_seconds=0,
        timed_set_duration_seconds=0,
        total_distance_meters=Decimal("0.00"),
        total_load_volume=Decimal("0.000"),
        average_rpe=None,
    )

    assert aggregate.completed_workouts == 0
    assert aggregate.total_load_volume == Decimal("0.000")
    assert aggregate.average_rpe is None


def test_progress_aggregate_rejects_invalid_average_rpe() -> None:
    payload = {
        **build_progress_aggregate().model_dump(),
        "average_rpe": Decimal("10.1"),
    }

    with pytest.raises(ValidationError):
        ProgressAggregateResponse.model_validate(payload)


def test_exercise_progress_response_serializes_nullable_metrics() -> None:
    exercise_id = uuid4()
    workout_id = uuid4()

    response = ExerciseProgressResponse(
        exercise_id=exercise_id,
        exercise_name="Bench Press",
        period=ProgressPeriodResponse(
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
            timezone="UTC",
        ),
        points=[
            ExerciseProgressPointResponse(
                workout_id=workout_id,
                started_at=datetime(2026, 1, 10, 10, 0, tzinfo=UTC),
                work_set_count=3,
                max_weight_kg=Decimal("100.000"),
                max_reps=8,
                max_set_volume=Decimal("800.000"),
                estimated_1rm_kg=Decimal("126.667"),
                total_load_volume=Decimal("2200.000"),
                max_distance_meters=None,
                total_distance_meters=Decimal("0.00"),
                longest_duration_seconds=None,
                timed_set_duration_seconds=0,
                best_pace_seconds_per_km=None,
                average_rpe=Decimal("8.5"),
            )
        ],
    )

    response_data = response.model_dump(mode="json")
    point_data = response_data["points"][0]

    assert response_data["exercise_id"] == str(exercise_id)
    assert point_data["workout_id"] == str(workout_id)
    assert point_data["started_at"] == "2026-01-10T10:00:00Z"
    assert point_data["max_weight_kg"] == "100.000"
    assert point_data["estimated_1rm_kg"] == "126.667"
    assert point_data["max_distance_meters"] is None
    assert point_data["best_pace_seconds_per_km"] is None


def test_personal_record_response_preserves_provenance() -> None:
    exercise_id = uuid4()
    workout_id = uuid4()
    workout_exercise_id = uuid4()
    workout_set_id = uuid4()

    record = PersonalRecordResponse(
        exercise_id=exercise_id,
        exercise_name="Deadlift",
        record_type=PersonalRecordType.MAX_WEIGHT,
        value=Decimal("180.000"),
        workout_id=workout_id,
        workout_exercise_id=workout_exercise_id,
        workout_set_id=workout_set_id,
        achieved_at=datetime(2026, 1, 20, 18, 30, tzinfo=UTC),
        reps=1,
        weight_kg=Decimal("180.000"),
        duration_seconds=None,
        distance_meters=None,
    )

    record_data = record.model_dump(mode="json")

    assert record_data["record_type"] == "max_weight"
    assert record_data["value"] == "180.000"
    assert record_data["workout_id"] == str(workout_id)
    assert record_data["workout_exercise_id"] == str(workout_exercise_id)
    assert record_data["workout_set_id"] == str(workout_set_id)
    assert record_data["achieved_at"] == "2026-01-20T18:30:00Z"


def test_personal_record_list_response_contains_pagination_metadata() -> None:
    record = PersonalRecordResponse(
        exercise_id=uuid4(),
        exercise_name="Pull-Up",
        record_type=PersonalRecordType.MAX_REPS,
        value=Decimal("15"),
        workout_id=uuid4(),
        workout_exercise_id=uuid4(),
        workout_set_id=uuid4(),
        achieved_at=datetime(2026, 1, 20, 18, 30, tzinfo=UTC),
        reps=15,
        weight_kg=Decimal("0.000"),
        duration_seconds=None,
        distance_meters=None,
    )

    response = PersonalRecordListResponse(
        items=[record],
        total=1,
        limit=20,
        offset=0,
    )

    assert response.items == [record]
    assert response.total == 1
    assert response.limit == 20
    assert response.offset == 0


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            ProgressAggregateResponse,
            {
                **build_progress_aggregate().model_dump(),
                "total_load_volume": Decimal("1.2345"),
            },
        ),
        (
            ProgressAggregateResponse,
            {
                **build_progress_aggregate().model_dump(),
                "total_distance_meters": Decimal("1.234"),
            },
        ),
        (
            ProgressAggregateResponse,
            {
                **build_progress_aggregate().model_dump(),
                "average_rpe": Decimal("8.25"),
            },
        ),
    ],
)
def test_progress_responses_require_pre_rounded_decimals(
    model: type[ProgressAggregateResponse],
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(payload)
