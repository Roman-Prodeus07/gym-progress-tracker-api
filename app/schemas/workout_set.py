from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

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

WorkoutSetType = Literal[
    "warmup",
    "working",
    "drop",
    "failure",
]

WeightKg = Annotated[
    Decimal,
    Field(
        ge=0,
        max_digits=7,
        decimal_places=3,
    ),
]
DistanceMeters = Annotated[
    Decimal,
    Field(
        gt=0,
        max_digits=9,
        decimal_places=2,
    ),
]
RpeValue = Annotated[
    Decimal,
    Field(
        ge=0,
        le=10,
        max_digits=3,
        decimal_places=1,
    ),
]


class WorkoutSetCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    set_number: PositiveInt | None = None
    set_type: WorkoutSetType = "working"
    reps: NonNegativeInt | None = None
    weight_kg: WeightKg | None = None
    duration_seconds: PositiveInt | None = None
    distance_meters: DistanceMeters | None = None
    rpe: RpeValue | None = None
    notes: Annotated[str | None, Field(max_length=2000)] = None

    @field_validator("set_number", mode="before")
    @classmethod
    def reject_explicit_null_set_number(cls, value: object) -> object:
        if value is None:
            raise ValueError("Field cannot be null.")
        return value

    @model_validator(mode="after")
    def require_performance_metric(self) -> WorkoutSetCreate:
        if (
            self.reps is None
            and self.duration_seconds is None
            and self.distance_meters is None
        ):
            raise ValueError("At least one performance metric must be provided.")

        return self


class WorkoutSetUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    set_number: PositiveInt | None = None
    set_type: WorkoutSetType | None = None
    reps: NonNegativeInt | None = None
    weight_kg: WeightKg | None = None
    duration_seconds: PositiveInt | None = None
    distance_meters: DistanceMeters | None = None
    rpe: RpeValue | None = None
    notes: Annotated[str | None, Field(max_length=2000)] = None

    @field_validator("set_number", "set_type", mode="before")
    @classmethod
    def reject_null_for_required_database_fields(
        cls,
        value: object,
    ) -> object:
        if value is None:
            raise ValueError("Field cannot be null.")
        return value

    @model_validator(mode="after")
    def validate_update(self) -> WorkoutSetUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")

        performance_fields = {
            "reps",
            "duration_seconds",
            "distance_meters",
        }

        if (
            performance_fields.issubset(self.model_fields_set)
            and self.reps is None
            and self.duration_seconds is None
            and self.distance_meters is None
        ):
            raise ValueError("At least one performance metric must be provided.")

        return self


class WorkoutSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    set_number: PositiveInt
    set_type: WorkoutSetType
    reps: NonNegativeInt | None
    weight_kg: WeightKg | None
    duration_seconds: PositiveInt | None
    distance_meters: DistanceMeters | None
    rpe: RpeValue | None
    notes: str | None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class WorkoutSetListResponse(BaseModel):
    items: list[WorkoutSetResponse]
    total: NonNegativeInt
    limit: PositiveInt
    offset: NonNegativeInt
