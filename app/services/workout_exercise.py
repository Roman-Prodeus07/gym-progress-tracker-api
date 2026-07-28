from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Exercise, WorkoutExercise, WorkoutSession
from app.schemas import WorkoutExerciseCreate, WorkoutExerciseUpdate

POSITION_CONSTRAINT_NAME = "uq_workout_exercises_session_position"


class ActiveExerciseNotFoundError(Exception):
    """Raised when an active catalogue exercise cannot be found."""


class WorkoutExercisePositionConflictError(Exception):
    """Raised when a workout already contains the requested position."""


def _is_position_conflict(error: IntegrityError) -> bool:
    diagnostic = getattr(error.orig, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)

    return constraint_name == POSITION_CONSTRAINT_NAME


async def _commit_workout_exercise_change(
    session: AsyncSession,
) -> None:
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()

        if _is_position_conflict(error):
            raise WorkoutExercisePositionConflictError from error

        raise
    except SQLAlchemyError:
        await session.rollback()
        raise


async def create_workout_exercise(
    session: AsyncSession,
    workout_id: UUID,
    user_id: UUID,
    workout_exercise_data: WorkoutExerciseCreate,
) -> WorkoutExercise | None:
    workout = await session.scalar(
        select(WorkoutSession)
        .where(
            WorkoutSession.id == workout_id,
            WorkoutSession.user_id == user_id,
        )
        .with_for_update()
    )

    if workout is None:
        return None

    exercise = await session.scalar(
        select(Exercise).where(
            Exercise.id == workout_exercise_data.exercise_id,
            Exercise.is_active.is_(True),
        )
    )

    if exercise is None:
        raise ActiveExerciseNotFoundError

    position = workout_exercise_data.position

    if position is None:
        position = (
            await session.scalar(
                select(
                    func.coalesce(
                        func.max(WorkoutExercise.position),
                        0,
                    )
                    + 1
                ).where(
                    WorkoutExercise.workout_session_id == workout_id,
                )
            )
            or 1
        )

    workout_exercise = WorkoutExercise(
        workout_session_id=workout.id,
        exercise=exercise,
        position=position,
        rest_seconds=workout_exercise_data.rest_seconds,
        notes=workout_exercise_data.notes,
    )
    session.add(workout_exercise)

    await _commit_workout_exercise_change(session)
    await session.refresh(workout_exercise)
    await session.refresh(
        workout_exercise,
        attribute_names=["exercise"],
    )

    return workout_exercise


async def list_owned_workout_exercises(
    session: AsyncSession,
    workout_id: UUID,
    user_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[WorkoutExercise], int] | None:
    owned_workout_id = await session.scalar(
        select(WorkoutSession.id).where(
            WorkoutSession.id == workout_id,
            WorkoutSession.user_id == user_id,
        )
    )

    if owned_workout_id is None:
        return None

    ownership_filter = (
        WorkoutExercise.workout_session_id == workout_id,
        WorkoutSession.user_id == user_id,
    )

    total = await session.scalar(
        select(func.count())
        .select_from(WorkoutExercise)
        .join(WorkoutSession)
        .where(*ownership_filter)
    )

    result = await session.scalars(
        select(WorkoutExercise)
        .join(WorkoutSession)
        .where(*ownership_filter)
        .options(selectinload(WorkoutExercise.exercise))
        .order_by(
            WorkoutExercise.position.asc(),
            WorkoutExercise.id.asc(),
        )
        .limit(limit)
        .offset(offset)
    )

    return list(result.all()), total or 0


async def get_owned_workout_exercise(
    session: AsyncSession,
    workout_id: UUID,
    workout_exercise_id: UUID,
    user_id: UUID,
) -> WorkoutExercise | None:
    return await session.scalar(
        select(WorkoutExercise)
        .join(WorkoutSession)
        .where(
            WorkoutExercise.id == workout_exercise_id,
            WorkoutExercise.workout_session_id == workout_id,
            WorkoutSession.user_id == user_id,
        )
        .options(selectinload(WorkoutExercise.exercise))
    )


async def update_workout_exercise(
    session: AsyncSession,
    workout_exercise: WorkoutExercise,
    workout_exercise_data: WorkoutExerciseUpdate,
) -> WorkoutExercise:
    if "exercise_id" in workout_exercise_data.model_fields_set:
        exercise_id = workout_exercise_data.exercise_id
        assert exercise_id is not None

        exercise = await session.scalar(
            select(Exercise).where(
                Exercise.id == exercise_id,
                Exercise.is_active.is_(True),
            )
        )

        if exercise is None:
            raise ActiveExerciseNotFoundError

        workout_exercise.exercise_id = exercise.id
        workout_exercise.exercise = exercise

    update_values = workout_exercise_data.model_dump(
        exclude_unset=True,
        exclude={"exercise_id"},
    )

    for field_name, value in update_values.items():
        setattr(workout_exercise, field_name, value)

    await _commit_workout_exercise_change(session)
    await session.refresh(workout_exercise)
    await session.refresh(
        workout_exercise,
        attribute_names=["exercise"],
    )

    return workout_exercise


async def delete_workout_exercise(
    session: AsyncSession,
    workout_exercise: WorkoutExercise,
) -> None:
    await session.delete(workout_exercise)
    await _commit_workout_exercise_change(session)
