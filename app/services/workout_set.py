from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WorkoutExercise, WorkoutSession, WorkoutSet
from app.schemas import WorkoutSetCreate, WorkoutSetUpdate

SET_NUMBER_CONSTRAINT_NAME = "uq_workout_sets_exercise_set_number"


class WorkoutSetNumberConflictError(Exception):
    """Raised when a workout exercise already contains the set number."""


class WorkoutSetPerformanceMetricRequiredError(Exception):
    """Raised when an update would remove every performance metric."""


def _is_set_number_conflict(error: IntegrityError) -> bool:
    diagnostic = getattr(error.orig, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)

    return constraint_name == SET_NUMBER_CONSTRAINT_NAME


async def _commit_workout_set_change(
    session: AsyncSession,
) -> None:
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()

        if _is_set_number_conflict(error):
            raise WorkoutSetNumberConflictError from error

        raise
    except SQLAlchemyError:
        await session.rollback()
        raise


async def create_workout_set(
    session: AsyncSession,
    workout_id: UUID,
    workout_exercise_id: UUID,
    user_id: UUID,
    workout_set_data: WorkoutSetCreate,
) -> WorkoutSet | None:
    workout_exercise = await session.scalar(
        select(WorkoutExercise)
        .join(
            WorkoutSession,
            WorkoutExercise.workout_session_id == WorkoutSession.id,
        )
        .where(
            WorkoutExercise.id == workout_exercise_id,
            WorkoutExercise.workout_session_id == workout_id,
            WorkoutSession.user_id == user_id,
        )
        .with_for_update()
    )

    if workout_exercise is None:
        return None

    set_number = workout_set_data.set_number

    if set_number is None:
        set_number = (
            await session.scalar(
                select(
                    func.coalesce(
                        func.max(WorkoutSet.set_number),
                        0,
                    )
                    + 1
                ).where(
                    WorkoutSet.workout_exercise_id == workout_exercise_id,
                )
            )
            or 1
        )

    create_values = workout_set_data.model_dump(
        exclude={"set_number"},
    )

    workout_set = WorkoutSet(
        workout_exercise_id=workout_exercise.id,
        set_number=set_number,
        **create_values,
    )
    session.add(workout_set)

    await _commit_workout_set_change(session)
    await session.refresh(workout_set)

    return workout_set


async def list_owned_workout_sets(
    session: AsyncSession,
    workout_id: UUID,
    workout_exercise_id: UUID,
    user_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[WorkoutSet], int] | None:
    owned_workout_exercise_id = await session.scalar(
        select(WorkoutExercise.id)
        .join(
            WorkoutSession,
            WorkoutExercise.workout_session_id == WorkoutSession.id,
        )
        .where(
            WorkoutExercise.id == workout_exercise_id,
            WorkoutExercise.workout_session_id == workout_id,
            WorkoutSession.user_id == user_id,
        )
    )

    if owned_workout_exercise_id is None:
        return None

    ownership_filter = (
        WorkoutSet.workout_exercise_id == workout_exercise_id,
        WorkoutExercise.workout_session_id == workout_id,
        WorkoutSession.user_id == user_id,
    )

    total = await session.scalar(
        select(func.count())
        .select_from(WorkoutSet)
        .join(
            WorkoutExercise,
            WorkoutSet.workout_exercise_id == WorkoutExercise.id,
        )
        .join(
            WorkoutSession,
            WorkoutExercise.workout_session_id == WorkoutSession.id,
        )
        .where(*ownership_filter)
    )

    result = await session.scalars(
        select(WorkoutSet)
        .join(
            WorkoutExercise,
            WorkoutSet.workout_exercise_id == WorkoutExercise.id,
        )
        .join(
            WorkoutSession,
            WorkoutExercise.workout_session_id == WorkoutSession.id,
        )
        .where(*ownership_filter)
        .order_by(
            WorkoutSet.set_number.asc(),
            WorkoutSet.id.asc(),
        )
        .limit(limit)
        .offset(offset)
    )

    return list(result.all()), total or 0


async def get_owned_workout_set(
    session: AsyncSession,
    workout_id: UUID,
    workout_exercise_id: UUID,
    workout_set_id: UUID,
    user_id: UUID,
) -> WorkoutSet | None:
    return await session.scalar(
        select(WorkoutSet)
        .join(
            WorkoutExercise,
            WorkoutSet.workout_exercise_id == WorkoutExercise.id,
        )
        .join(
            WorkoutSession,
            WorkoutExercise.workout_session_id == WorkoutSession.id,
        )
        .where(
            WorkoutSet.id == workout_set_id,
            WorkoutSet.workout_exercise_id == workout_exercise_id,
            WorkoutExercise.workout_session_id == workout_id,
            WorkoutSession.user_id == user_id,
        )
    )


async def update_workout_set(
    session: AsyncSession,
    workout_set: WorkoutSet,
    workout_set_data: WorkoutSetUpdate,
) -> WorkoutSet:
    update_values = workout_set_data.model_dump(exclude_unset=True)

    resulting_reps = update_values.get(
        "reps",
        workout_set.reps,
    )
    resulting_duration = update_values.get(
        "duration_seconds",
        workout_set.duration_seconds,
    )
    resulting_distance = update_values.get(
        "distance_meters",
        workout_set.distance_meters,
    )

    if (
        resulting_reps is None
        and resulting_duration is None
        and resulting_distance is None
    ):
        raise WorkoutSetPerformanceMetricRequiredError

    for field_name, value in update_values.items():
        setattr(workout_set, field_name, value)

    await _commit_workout_set_change(session)
    await session.refresh(workout_set)

    return workout_set


async def delete_workout_set(
    session: AsyncSession,
    workout_set: WorkoutSet,
) -> None:
    await session.delete(workout_set)
    await _commit_workout_set_change(session)
