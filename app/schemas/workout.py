from __future__ import annotations

from typing import Annotated
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

from app.schemas.workout_exercise import WorkoutExerciseDetailResponse


class WorkoutSessionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, max_length=120)]
    notes: Annotated[str | None, Field(max_length=2000)] = None
    started_at: AwareDatetime | None = None


class WorkoutSessionUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str | None, Field(min_length=1, max_length=120)] = None
    notes: Annotated[str | None, Field(max_length=2000)] = None
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None

    @field_validator("name", "started_at", mode="before")
    @classmethod
    def reject_null_for_required_database_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("Field cannot be null.")
        return value

    @model_validator(mode="after")
    def validate_update(self) -> WorkoutSessionUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")

        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValueError("completed_at cannot be earlier than started_at.")

        return self


class WorkoutSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    notes: str | None
    started_at: AwareDatetime
    completed_at: AwareDatetime | None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class WorkoutSessionDetailResponse(WorkoutSessionResponse):
    exercises: list[WorkoutExerciseDetailResponse] = Field(
        default_factory=list,
        validation_alias="workout_exercises",
    )


class WorkoutSessionListQuery(BaseModel):
    limit: Annotated[int, Field(ge=1, le=100)] = 20
    offset: Annotated[int, Field(ge=0)] = 0
    started_from: AwareDatetime | None = None
    started_to: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_started_at_range(self) -> WorkoutSessionListQuery:
        if (
            self.started_from is not None
            and self.started_to is not None
            and self.started_to < self.started_from
        ):
            raise ValueError("started_to cannot be earlier than started_from.")

        return self


class WorkoutSessionListResponse(BaseModel):
    items: list[WorkoutSessionResponse]
    total: NonNegativeInt
    limit: PositiveInt
    offset: NonNegativeInt
