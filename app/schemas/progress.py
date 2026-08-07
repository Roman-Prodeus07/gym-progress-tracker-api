from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Final
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveInt,
    field_validator,
    model_validator,
)

MAX_PROGRESS_RANGE_DAYS: Final = 366

ProgressDecimal = Annotated[
    Decimal,
    Field(
        ge=0,
        decimal_places=3,
    ),
]
DistanceDecimal = Annotated[
    Decimal,
    Field(
        ge=0,
        decimal_places=2,
    ),
]
PaceDecimal = Annotated[
    Decimal,
    Field(
        gt=0,
        decimal_places=3,
    ),
]
AverageRpeDecimal = Annotated[
    Decimal,
    Field(
        ge=0,
        le=10,
        decimal_places=1,
    ),
]


class ProgressBucket(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class PersonalRecordType(StrEnum):
    MAX_WEIGHT = "max_weight"
    MAX_REPS = "max_reps"
    MAX_SET_VOLUME = "max_set_volume"
    ESTIMATED_1RM = "estimated_1rm"
    MAX_DISTANCE = "max_distance"
    LONGEST_DURATION = "longest_duration"
    BEST_PACE = "best_pace"


class ProgressDateRangeParams(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    date_from: date
    date_to: date
    timezone: str = "UTC"

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("timezone must be a valid IANA timezone.") from exc

        return value

    @model_validator(mode="after")
    def validate_date_range(self) -> ProgressDateRangeParams:
        if self.date_from > self.date_to:
            raise ValueError("date_from cannot be later than date_to.")

        inclusive_days = (self.date_to - self.date_from).days + 1
        if inclusive_days > MAX_PROGRESS_RANGE_DAYS:
            raise ValueError(
                f"Date range cannot exceed {MAX_PROGRESS_RANGE_DAYS} days."
            )

        return self


class ProgressSummaryQuery(ProgressDateRangeParams):
    bucket: ProgressBucket = ProgressBucket.WEEK


class ProgressPeriodResponse(ProgressDateRangeParams):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )


class ProgressSummaryPeriodResponse(ProgressPeriodResponse):
    bucket: ProgressBucket


class ProgressAggregateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    completed_workouts: NonNegativeInt
    active_days: NonNegativeInt
    unique_exercises: NonNegativeInt
    recorded_set_count: NonNegativeInt
    work_set_count: NonNegativeInt
    workout_duration_seconds: NonNegativeInt
    timed_set_duration_seconds: NonNegativeInt
    total_distance_meters: DistanceDecimal
    total_load_volume: ProgressDecimal
    average_rpe: AverageRpeDecimal | None


class ProgressBucketResponse(ProgressAggregateResponse):
    bucket_start: date


class ProgressSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: ProgressSummaryPeriodResponse
    totals: ProgressAggregateResponse
    buckets: list[ProgressBucketResponse]


class ExerciseProgressPointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workout_id: UUID
    started_at: AwareDatetime
    work_set_count: NonNegativeInt
    max_weight_kg: ProgressDecimal | None
    max_reps: NonNegativeInt | None
    max_set_volume: ProgressDecimal | None
    estimated_1rm_kg: ProgressDecimal | None
    total_load_volume: ProgressDecimal
    max_distance_meters: DistanceDecimal | None
    total_distance_meters: DistanceDecimal
    longest_duration_seconds: PositiveInt | None
    timed_set_duration_seconds: NonNegativeInt
    best_pace_seconds_per_km: PaceDecimal | None
    average_rpe: AverageRpeDecimal | None


class ExerciseProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exercise_id: UUID
    exercise_name: str
    period: ProgressPeriodResponse
    points: list[ExerciseProgressPointResponse]


class PersonalRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exercise_id: UUID
    exercise_name: str
    record_type: PersonalRecordType
    value: ProgressDecimal
    workout_id: UUID
    workout_exercise_id: UUID
    workout_set_id: UUID
    achieved_at: AwareDatetime
    reps: NonNegativeInt | None
    weight_kg: ProgressDecimal | None
    duration_seconds: PositiveInt | None
    distance_meters: DistanceDecimal | None


class PersonalRecordListResponse(BaseModel):
    items: list[PersonalRecordResponse]
    total: NonNegativeInt
    limit: PositiveInt
    offset: NonNegativeInt
