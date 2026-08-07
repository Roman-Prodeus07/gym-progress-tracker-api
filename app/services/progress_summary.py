from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol, cast
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WorkoutExercise, WorkoutSession, WorkoutSet
from app.schemas import (
    ProgressAggregateResponse,
    ProgressBucketResponse,
    ProgressSummaryPeriodResponse,
    ProgressSummaryQuery,
    ProgressSummaryResponse,
)
from app.services.progress_calculations import (
    DISTANCE_QUANTUM,
    RPE_QUANTUM,
    THREE_PLACE_QUANTUM,
    WORKLOAD_SET_TYPES,
    ZERO,
    calculate_decimal_average,
    calculate_load_volume,
    round_decimal,
)
from app.services.progress_time import (
    build_bucket_starts,
    get_bucket_start,
    local_date_range_to_utc,
)


class ProgressSummaryCandidate(Protocol):
    workout_id: UUID
    started_at: datetime
    completed_at: datetime | None
    exercise_id: UUID | None
    workout_set_id: UUID | None
    set_type: str | None
    reps: int | None
    weight_kg: Decimal | None
    duration_seconds: int | None
    distance_meters: Decimal | None
    rpe: Decimal | None


@dataclass(slots=True)
class _ProgressAccumulator:
    workout_ids: set[UUID] = field(default_factory=set)
    active_dates: set[date] = field(default_factory=set)
    exercise_ids: set[UUID] = field(default_factory=set)
    recorded_set_ids: set[UUID] = field(default_factory=set)
    work_set_count: int = 0
    workout_duration_seconds: int = 0
    timed_set_duration_seconds: int = 0
    total_distance_meters: Decimal = ZERO
    total_load_volume: Decimal = ZERO
    rpe_values: list[Decimal] = field(default_factory=list)

    def add(
        self,
        candidate: ProgressSummaryCandidate,
        local_workout_date: date,
    ) -> None:
        if candidate.workout_id not in self.workout_ids:
            self.workout_ids.add(candidate.workout_id)
            self.active_dates.add(local_workout_date)

            if candidate.completed_at is not None:
                duration = candidate.completed_at - candidate.started_at
                self.workout_duration_seconds += int(duration.total_seconds())

        if candidate.exercise_id is not None:
            self.exercise_ids.add(candidate.exercise_id)

        if (
            candidate.workout_set_id is None
            or candidate.workout_set_id in self.recorded_set_ids
        ):
            return

        self.recorded_set_ids.add(candidate.workout_set_id)

        if candidate.set_type not in WORKLOAD_SET_TYPES:
            return

        self.work_set_count += 1
        self.total_load_volume += calculate_load_volume(
            candidate.weight_kg,
            candidate.reps,
        )

        if candidate.duration_seconds is not None:
            self.timed_set_duration_seconds += candidate.duration_seconds

        if candidate.distance_meters is not None:
            self.total_distance_meters += candidate.distance_meters

        if candidate.rpe is not None:
            self.rpe_values.append(candidate.rpe)

    def to_response(self) -> ProgressAggregateResponse:
        average_rpe = calculate_decimal_average(self.rpe_values)

        return ProgressAggregateResponse(
            completed_workouts=len(self.workout_ids),
            active_days=len(self.active_dates),
            unique_exercises=len(self.exercise_ids),
            recorded_set_count=len(self.recorded_set_ids),
            work_set_count=self.work_set_count,
            workout_duration_seconds=self.workout_duration_seconds,
            timed_set_duration_seconds=self.timed_set_duration_seconds,
            total_distance_meters=round_decimal(
                self.total_distance_meters,
                DISTANCE_QUANTUM,
            ),
            total_load_volume=round_decimal(
                self.total_load_volume,
                THREE_PLACE_QUANTUM,
            ),
            average_rpe=(
                round_decimal(average_rpe, RPE_QUANTUM)
                if average_rpe is not None
                else None
            ),
        )


def build_progress_summary(
    candidates: Iterable[ProgressSummaryCandidate],
    query: ProgressSummaryQuery,
) -> ProgressSummaryResponse:
    local_timezone = ZoneInfo(query.timezone)
    totals = _ProgressAccumulator()
    bucket_accumulators = {
        bucket_start: _ProgressAccumulator()
        for bucket_start in build_bucket_starts(
            query.date_from,
            query.date_to,
            query.bucket,
        )
    }

    for candidate in candidates:
        if candidate.completed_at is None:
            continue

        local_workout_date = candidate.started_at.astimezone(local_timezone).date()

        if not query.date_from <= local_workout_date <= query.date_to:
            continue

        bucket_start = get_bucket_start(local_workout_date, query.bucket)
        totals.add(candidate, local_workout_date)
        bucket_accumulators[bucket_start].add(candidate, local_workout_date)

    buckets = [
        ProgressBucketResponse(
            bucket_start=bucket_start,
            **accumulator.to_response().model_dump(),
        )
        for bucket_start, accumulator in bucket_accumulators.items()
    ]

    return ProgressSummaryResponse(
        period=ProgressSummaryPeriodResponse(
            date_from=query.date_from,
            date_to=query.date_to,
            timezone=query.timezone,
            bucket=query.bucket,
        ),
        totals=totals.to_response(),
        buckets=buckets,
    )


async def get_progress_summary(
    session: AsyncSession,
    user_id: UUID,
    query: ProgressSummaryQuery,
) -> ProgressSummaryResponse:
    utc_range = local_date_range_to_utc(
        query.date_from,
        query.date_to,
        query.timezone,
    )

    result = await session.execute(
        select(
            WorkoutSession.id.label("workout_id"),
            WorkoutSession.started_at.label("started_at"),
            WorkoutSession.completed_at.label("completed_at"),
            WorkoutExercise.exercise_id.label("exercise_id"),
            WorkoutSet.id.label("workout_set_id"),
            WorkoutSet.set_type.label("set_type"),
            WorkoutSet.reps.label("reps"),
            WorkoutSet.weight_kg.label("weight_kg"),
            WorkoutSet.duration_seconds.label("duration_seconds"),
            WorkoutSet.distance_meters.label("distance_meters"),
            WorkoutSet.rpe.label("rpe"),
        )
        .select_from(WorkoutSession)
        .outerjoin(
            WorkoutExercise,
            WorkoutExercise.workout_session_id == WorkoutSession.id,
        )
        .outerjoin(
            WorkoutSet,
            WorkoutSet.workout_exercise_id == WorkoutExercise.id,
        )
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.completed_at.is_not(None),
            WorkoutSession.started_at >= utc_range.start_inclusive,
            WorkoutSession.started_at < utc_range.end_exclusive,
        )
        .order_by(
            WorkoutSession.started_at,
            WorkoutSession.id,
            WorkoutExercise.position,
            WorkoutSet.set_number,
        )
    )

    candidates = cast(
        Iterable[ProgressSummaryCandidate],
        result.all(),
    )

    return build_progress_summary(candidates, query)
