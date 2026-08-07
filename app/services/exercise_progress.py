from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol, cast
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise, WorkoutExercise, WorkoutSession, WorkoutSet
from app.schemas import (
    ExerciseProgressPointResponse,
    ExerciseProgressResponse,
    ProgressDateRangeParams,
    ProgressPeriodResponse,
)
from app.services.progress_calculations import (
    DISTANCE_QUANTUM,
    RPE_QUANTUM,
    THREE_PLACE_QUANTUM,
    WORKLOAD_SET_TYPES,
    ZERO,
    calculate_decimal_average,
    calculate_estimated_1rm,
    calculate_load_volume,
    calculate_pace_seconds_per_km,
    round_decimal,
)
from app.services.progress_time import local_date_range_to_utc


class ExerciseProgressCandidate(Protocol):
    workout_id: UUID
    started_at: datetime
    completed_at: datetime | None
    workout_set_id: UUID | None
    set_type: str | None
    reps: int | None
    weight_kg: Decimal | None
    duration_seconds: int | None
    distance_meters: Decimal | None
    rpe: Decimal | None


@dataclass(slots=True)
class _ExerciseProgressAccumulator:
    workout_id: UUID
    started_at: datetime
    workout_set_ids: set[UUID] = field(default_factory=set)
    work_set_count: int = 0
    max_weight_kg: Decimal | None = None
    max_reps: int | None = None
    max_set_volume: Decimal | None = None
    estimated_1rm_kg: Decimal | None = None
    total_load_volume: Decimal = ZERO
    max_distance_meters: Decimal | None = None
    total_distance_meters: Decimal = ZERO
    longest_duration_seconds: int | None = None
    timed_set_duration_seconds: int = 0
    best_pace_seconds_per_km: Decimal | None = None
    rpe_values: list[Decimal] = field(default_factory=list)

    def add(self, candidate: ExerciseProgressCandidate) -> None:
        if (
            candidate.workout_set_id is None
            or candidate.workout_set_id in self.workout_set_ids
        ):
            return

        self.workout_set_ids.add(candidate.workout_set_id)

        if candidate.set_type not in WORKLOAD_SET_TYPES:
            return

        self.work_set_count += 1

        if candidate.weight_kg is not None:
            self.max_weight_kg = _max_optional(
                self.max_weight_kg,
                candidate.weight_kg,
            )

        if candidate.reps is not None:
            self.max_reps = _max_optional(
                self.max_reps,
                candidate.reps,
            )

        set_volume = calculate_load_volume(
            candidate.weight_kg,
            candidate.reps,
        )
        self.total_load_volume += set_volume

        if candidate.weight_kg is not None and candidate.reps is not None:
            self.max_set_volume = _max_optional(
                self.max_set_volume,
                set_volume,
            )

        estimated_1rm = calculate_estimated_1rm(
            candidate.weight_kg,
            candidate.reps,
        )
        if estimated_1rm is not None:
            self.estimated_1rm_kg = _max_optional(
                self.estimated_1rm_kg,
                estimated_1rm,
            )

        if candidate.distance_meters is not None:
            self.max_distance_meters = _max_optional(
                self.max_distance_meters,
                candidate.distance_meters,
            )
            self.total_distance_meters += candidate.distance_meters

        if candidate.duration_seconds is not None:
            self.longest_duration_seconds = _max_optional(
                self.longest_duration_seconds,
                candidate.duration_seconds,
            )
            self.timed_set_duration_seconds += candidate.duration_seconds

        pace = calculate_pace_seconds_per_km(
            candidate.distance_meters,
            candidate.duration_seconds,
        )
        if pace is not None:
            self.best_pace_seconds_per_km = _min_optional(
                self.best_pace_seconds_per_km,
                pace,
            )

        if candidate.rpe is not None:
            self.rpe_values.append(candidate.rpe)

    def to_response(self) -> ExerciseProgressPointResponse:
        average_rpe = calculate_decimal_average(self.rpe_values)

        return ExerciseProgressPointResponse(
            workout_id=self.workout_id,
            started_at=self.started_at,
            work_set_count=self.work_set_count,
            max_weight_kg=_round_optional(
                self.max_weight_kg,
                THREE_PLACE_QUANTUM,
            ),
            max_reps=self.max_reps,
            max_set_volume=_round_optional(
                self.max_set_volume,
                THREE_PLACE_QUANTUM,
            ),
            estimated_1rm_kg=_round_optional(
                self.estimated_1rm_kg,
                THREE_PLACE_QUANTUM,
            ),
            total_load_volume=round_decimal(
                self.total_load_volume,
                THREE_PLACE_QUANTUM,
            ),
            max_distance_meters=_round_optional(
                self.max_distance_meters,
                DISTANCE_QUANTUM,
            ),
            total_distance_meters=round_decimal(
                self.total_distance_meters,
                DISTANCE_QUANTUM,
            ),
            longest_duration_seconds=self.longest_duration_seconds,
            timed_set_duration_seconds=self.timed_set_duration_seconds,
            best_pace_seconds_per_km=_round_optional(
                self.best_pace_seconds_per_km,
                THREE_PLACE_QUANTUM,
            ),
            average_rpe=(
                round_decimal(average_rpe, RPE_QUANTUM)
                if average_rpe is not None
                else None
            ),
        )


def _max_optional[T: (int, Decimal)](current: T | None, candidate: T) -> T:
    if current is None or candidate > current:
        return candidate

    return current


def _min_optional[T: (int, Decimal)](current: T | None, candidate: T) -> T:
    if current is None or candidate < current:
        return candidate

    return current


def _round_optional(
    value: Decimal | None,
    quantum: Decimal,
) -> Decimal | None:
    if value is None:
        return None

    return round_decimal(value, quantum)


def build_exercise_progress(
    exercise_id: UUID,
    exercise_name: str,
    candidates: Iterable[ExerciseProgressCandidate],
    query: ProgressDateRangeParams,
) -> ExerciseProgressResponse:
    local_timezone = ZoneInfo(query.timezone)
    accumulators: dict[UUID, _ExerciseProgressAccumulator] = {}

    for candidate in candidates:
        if candidate.completed_at is None:
            continue

        local_workout_date: date = candidate.started_at.astimezone(
            local_timezone
        ).date()
        if not query.date_from <= local_workout_date <= query.date_to:
            continue

        accumulator = accumulators.setdefault(
            candidate.workout_id,
            _ExerciseProgressAccumulator(
                workout_id=candidate.workout_id,
                started_at=candidate.started_at,
            ),
        )
        accumulator.add(candidate)

    points = sorted(
        (accumulator.to_response() for accumulator in accumulators.values()),
        key=lambda point: (point.started_at, point.workout_id),
    )

    return ExerciseProgressResponse(
        exercise_id=exercise_id,
        exercise_name=exercise_name,
        period=ProgressPeriodResponse(
            date_from=query.date_from,
            date_to=query.date_to,
            timezone=query.timezone,
        ),
        points=points,
    )


async def get_exercise_progress(
    session: AsyncSession,
    user_id: UUID,
    exercise_id: UUID,
    query: ProgressDateRangeParams,
) -> ExerciseProgressResponse | None:
    exercise_name = await session.scalar(
        select(Exercise.name).where(Exercise.id == exercise_id)
    )
    if exercise_name is None:
        return None

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
            WorkoutSet.id.label("workout_set_id"),
            WorkoutSet.set_type.label("set_type"),
            WorkoutSet.reps.label("reps"),
            WorkoutSet.weight_kg.label("weight_kg"),
            WorkoutSet.duration_seconds.label("duration_seconds"),
            WorkoutSet.distance_meters.label("distance_meters"),
            WorkoutSet.rpe.label("rpe"),
        )
        .select_from(WorkoutSession)
        .join(
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
            WorkoutExercise.exercise_id == exercise_id,
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
        Iterable[ExerciseProgressCandidate],
        result.all(),
    )

    return build_exercise_progress(
        exercise_id,
        exercise_name,
        candidates,
        query,
    )
