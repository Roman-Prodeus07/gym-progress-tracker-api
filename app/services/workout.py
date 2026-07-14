from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WorkoutSession
from app.schemas import WorkoutSessionCreate, WorkoutSessionUpdate


class InvalidWorkoutTimeRangeError(Exception):
    """Raised when workout completion is earlier than its start."""


async def create_workout_session(
    session: AsyncSession,
    user_id: UUID,
    workout_data: WorkoutSessionCreate,
) -> WorkoutSession:
    workout_values = workout_data.model_dump(exclude_none=True)

    workout = WorkoutSession(
        user_id=user_id,
        **workout_values,
    )
    session.add(workout)

    try:
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise

    await session.refresh(workout)
    return workout


async def list_workout_sessions(
    session: AsyncSession,
    user_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[WorkoutSession], int]:
    ownership_filter = WorkoutSession.user_id == user_id

    total = await session.scalar(
        select(func.count()).select_from(WorkoutSession).where(ownership_filter)
    )

    result = await session.scalars(
        select(WorkoutSession)
        .where(ownership_filter)
        .order_by(
            WorkoutSession.started_at.desc(),
            WorkoutSession.created_at.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    return list(result.all()), total or 0


async def get_owned_workout_session(
    session: AsyncSession,
    workout_id: UUID,
    user_id: UUID,
) -> WorkoutSession | None:
    return await session.scalar(
        select(WorkoutSession).where(
            WorkoutSession.id == workout_id,
            WorkoutSession.user_id == user_id,
        )
    )


async def update_workout_session(
    session: AsyncSession,
    workout: WorkoutSession,
    workout_data: WorkoutSessionUpdate,
) -> WorkoutSession:
    update_values = workout_data.model_dump(exclude_unset=True)

    candidate_started_at: datetime = update_values.get(
        "started_at",
        workout.started_at,
    )
    candidate_completed_at: datetime | None = update_values.get(
        "completed_at",
        workout.completed_at,
    )

    if (
        candidate_completed_at is not None
        and candidate_completed_at < candidate_started_at
    ):
        raise InvalidWorkoutTimeRangeError

    for field_name, value in update_values.items():
        setattr(workout, field_name, value)

    try:
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise

    await session.refresh(workout)
    return workout


async def delete_workout_session(
    session: AsyncSession,
    workout: WorkoutSession,
) -> None:
    await session.delete(workout)

    try:
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise
