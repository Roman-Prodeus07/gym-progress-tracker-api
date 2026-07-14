from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.exercise import Exercise
    from app.models.workout_session import WorkoutSession
    from app.models.workout_set import WorkoutSet


class WorkoutExercise(TimestampMixin, Base):
    __tablename__ = "workout_exercises"
    __table_args__ = (
        CheckConstraint(
            "position > 0",
            name="ck_workout_exercises_position_positive",
        ),
        CheckConstraint(
            "rest_seconds IS NULL OR rest_seconds > 0",
            name="ck_workout_exercises_rest_seconds_positive",
        ),
        UniqueConstraint(
            "workout_session_id",
            "position",
            name="uq_workout_exercises_session_position",
        ),
        Index(
            "ix_workout_exercises_exercise_id",
            "exercise_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    workout_session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    rest_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    workout_session: Mapped[WorkoutSession] = relationship(
        "WorkoutSession",
        back_populates="workout_exercises",
    )
    exercise: Mapped[Exercise] = relationship(
        "Exercise",
        back_populates="workout_exercises",
    )
    workout_sets: Mapped[list[WorkoutSet]] = relationship(
        "WorkoutSet",
        back_populates="workout_exercise",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="WorkoutSet.set_number",
    )
