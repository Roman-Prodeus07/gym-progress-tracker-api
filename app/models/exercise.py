from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.workout_exercise import WorkoutExercise


class Exercise(TimestampMixin, Base):
    __tablename__ = "exercises"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(140),
        unique=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    primary_muscle_group: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    equipment: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
    )

    workout_exercises: Mapped[list[WorkoutExercise]] = relationship(
        "WorkoutExercise",
        back_populates="exercise",
        passive_deletes=True,
    )
