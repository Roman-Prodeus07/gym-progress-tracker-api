from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise


async def list_active_exercises(
    session: AsyncSession,
    limit: int,
    offset: int,
) -> tuple[list[Exercise], int]:
    active_filter = Exercise.is_active.is_(True)

    total = await session.scalar(
        select(func.count()).select_from(Exercise).where(active_filter)
    )

    result = await session.scalars(
        select(Exercise)
        .where(active_filter)
        .order_by(
            Exercise.name.asc(),
            Exercise.id.asc(),
        )
        .limit(limit)
        .offset(offset)
    )

    return list(result.all()), total or 0


async def get_active_exercise(
    session: AsyncSession,
    exercise_id: UUID,
) -> Exercise | None:
    return await session.scalar(
        select(Exercise).where(
            Exercise.id == exercise_id,
            Exercise.is_active.is_(True),
        )
    )
