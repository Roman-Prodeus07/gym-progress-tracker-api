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

from app.schemas.exercise import ExerciseResponse


class WorkoutExerciseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    exercise_id: UUID
    position: PositiveInt | None = None
    rest_seconds: PositiveInt | None = None
    notes: Annotated[str | None, Field(max_length=2000)] = None

    @field_validator("position", mode="before")
    @classmethod
    def reject_explicit_null_position(cls, value: object) -> object:
        if value is None:
            raise ValueError("Field cannot be null.")
        return value


class WorkoutExerciseUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    exercise_id: UUID | None = None
    position: PositiveInt | None = None
    rest_seconds: PositiveInt | None = None
    notes: Annotated[str | None, Field(max_length=2000)] = None

    @field_validator("exercise_id", "position", mode="before")
    @classmethod
    def reject_null_for_required_database_fields(
        cls,
        value: object,
    ) -> object:
        if value is None:
            raise ValueError("Field cannot be null.")
        return value

    @model_validator(mode="after")
    def validate_update(self) -> WorkoutExerciseUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")

        return self


class WorkoutExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exercise_id: UUID
    exercise: ExerciseResponse
    position: PositiveInt
    rest_seconds: PositiveInt | None
    notes: str | None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class WorkoutExerciseListResponse(BaseModel):
    items: list[WorkoutExerciseResponse]
    total: NonNegativeInt
    limit: PositiveInt
    offset: NonNegativeInt
