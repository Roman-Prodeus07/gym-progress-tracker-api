from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workout_exercise import WorkoutExercise


class WorkoutSession(TimestampMixin, Base):
    __tablename__ = "workout_sessions"
    __table_args__ = (
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="ck_workout_sessions_completed_after_started",
        ),
        Index(
            "ix_workout_sessions_user_id_started_at",
            "user_id",
            "started_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(
        "User",
        back_populates="workout_sessions",
    )
    workout_exercises: Mapped[list[WorkoutExercise]] = relationship(
        "WorkoutExercise",
        back_populates="workout_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="WorkoutExercise.position",
    )
