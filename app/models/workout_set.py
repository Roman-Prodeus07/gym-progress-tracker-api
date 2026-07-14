from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.workout_exercise import WorkoutExercise


class WorkoutSet(TimestampMixin, Base):
    __tablename__ = "workout_sets"
    __table_args__ = (
        CheckConstraint(
            "set_number > 0",
            name="ck_workout_sets_set_number_positive",
        ),
        CheckConstraint(
            "set_type IN ('warmup', 'working', 'drop', 'failure')",
            name="ck_workout_sets_set_type_allowed",
        ),
        CheckConstraint(
            "reps IS NULL OR reps >= 0",
            name="ck_workout_sets_reps_non_negative",
        ),
        CheckConstraint(
            "weight_kg IS NULL OR weight_kg >= 0",
            name="ck_workout_sets_weight_non_negative",
        ),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds > 0",
            name="ck_workout_sets_duration_positive",
        ),
        CheckConstraint(
            "distance_meters IS NULL OR distance_meters > 0",
            name="ck_workout_sets_distance_positive",
        ),
        CheckConstraint(
            "rpe IS NULL OR (rpe >= 0 AND rpe <= 10)",
            name="ck_workout_sets_rpe_range",
        ),
        CheckConstraint(
            "reps IS NOT NULL OR duration_seconds IS NOT NULL "
            "OR distance_meters IS NOT NULL",
            name="ck_workout_sets_performance_metric_required",
        ),
        UniqueConstraint(
            "workout_exercise_id",
            "set_number",
            name="uq_workout_sets_exercise_set_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    workout_exercise_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workout_exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    set_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    set_type: Mapped[str] = mapped_column(
        String(20),
        default="working",
        server_default=text("'working'"),
        nullable=False,
    )
    reps: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 3),
        nullable=True,
    )
    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    distance_meters: Mapped[Decimal | None] = mapped_column(
        Numeric(9, 2),
        nullable=True,
    )
    rpe: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 1),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    workout_exercise: Mapped[WorkoutExercise] = relationship(
        "WorkoutExercise",
        back_populates="workout_sets",
    )
