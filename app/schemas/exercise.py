from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    NonNegativeInt,
    PositiveInt,
)


class ExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str | None
    primary_muscle_group: str
    equipment: str
    created_at: AwareDatetime
    updated_at: AwareDatetime


class ExerciseListResponse(BaseModel):
    items: list[ExerciseResponse]
    total: NonNegativeInt
    limit: PositiveInt
    offset: NonNegativeInt
