from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models import Exercise
from app.schemas import WorkoutExerciseCreate, WorkoutExerciseUpdate
from app.services import (
    ActiveExerciseNotFoundError,
    WorkoutExercisePositionConflictError,
    create_workout_exercise,
    delete_workout_exercise,
    get_owned_workout_exercise,
    list_owned_workout_exercises,
    update_workout_exercise,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_exercise() -> Exercise:
    return Exercise(
        id=uuid4(),
        name="Bench Press",
        slug="bench-press",
        description=None,
        primary_muscle_group="chest",
        equipment="barbell",
        is_active=True,
    )


@pytest.mark.anyio
async def test_create_workout_exercise_assigns_next_position() -> None:
    workout_id = uuid4()
    user_id = uuid4()
    workout = SimpleNamespace(id=workout_id)
    exercise = make_exercise()
    session = SimpleNamespace(
        scalar=AsyncMock(
            side_effect=[
                workout,
                exercise,
                3,
            ]
        ),
        add=Mock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    result = await create_workout_exercise(
        session,
        workout_id,
        user_id,
        WorkoutExerciseCreate(
            exercise_id=exercise.id,
            rest_seconds=90,
        ),
    )

    workout_statement = session.scalar.await_args_list[0].args[0]
    exercise_statement = session.scalar.await_args_list[1].args[0]
    position_statement = session.scalar.await_args_list[2].args[0]

    assert result is not None
    assert result.workout_session_id == workout_id
    assert result.exercise is exercise
    assert result.position == 3
    assert result.rest_seconds == 90

    assert workout_id in workout_statement.compile().params.values()
    assert user_id in workout_statement.compile().params.values()
    assert "FOR UPDATE" in str(workout_statement)

    assert exercise.id in exercise_statement.compile().params.values()
    assert "exercises.is_active IS true" in str(exercise_statement)

    assert workout_id in position_statement.compile().params.values()
    assert "max(workout_exercises.position)" in str(position_statement)

    session.add.assert_called_once_with(result)
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    assert session.refresh.await_args_list == [
        call(result),
        call(result, attribute_names=["exercise"]),
    ]


@pytest.mark.anyio
async def test_create_workout_exercise_uses_explicit_position() -> None:
    workout_id = uuid4()
    workout = SimpleNamespace(id=workout_id)
    exercise = make_exercise()
    session = SimpleNamespace(
        scalar=AsyncMock(
            side_effect=[
                workout,
                exercise,
            ]
        ),
        add=Mock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    result = await create_workout_exercise(
        session,
        workout_id,
        uuid4(),
        WorkoutExerciseCreate(
            exercise_id=exercise.id,
            position=4,
        ),
    )

    assert result is not None
    assert result.position == 4
    assert session.scalar.await_count == 2


@pytest.mark.anyio
async def test_create_workout_exercise_hides_unowned_workout() -> None:
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=None),
        add=Mock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    result = await create_workout_exercise(
        session,
        uuid4(),
        uuid4(),
        WorkoutExerciseCreate(exercise_id=uuid4()),
    )

    assert result is None
    session.add.assert_not_called()
    session.commit.assert_not_awaited()
    session.refresh.assert_not_awaited()


@pytest.mark.anyio
async def test_create_workout_exercise_requires_active_exercise() -> None:
    workout = SimpleNamespace(id=uuid4())
    session = SimpleNamespace(
        scalar=AsyncMock(
            side_effect=[
                workout,
                None,
            ]
        ),
        add=Mock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    with pytest.raises(ActiveExerciseNotFoundError):
        await create_workout_exercise(
            session,
            workout.id,
            uuid4(),
            WorkoutExerciseCreate(exercise_id=uuid4()),
        )

    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_list_owned_workout_exercises_hides_unowned_workout() -> None:
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=None),
        scalars=AsyncMock(),
    )

    result = await list_owned_workout_exercises(
        session,
        uuid4(),
        uuid4(),
        limit=20,
        offset=0,
    )

    assert result is None
    session.scalars.assert_not_awaited()


@pytest.mark.anyio
async def test_list_owned_workout_exercises_filters_and_orders() -> None:
    workout_id = uuid4()
    user_id = uuid4()
    workout_exercises = [
        SimpleNamespace(id=uuid4(), position=1),
        SimpleNamespace(id=uuid4(), position=2),
    ]
    scalar_result = SimpleNamespace(
        all=Mock(return_value=workout_exercises),
    )
    session = SimpleNamespace(
        scalar=AsyncMock(
            side_effect=[
                workout_id,
                2,
            ]
        ),
        scalars=AsyncMock(return_value=scalar_result),
    )

    result = await list_owned_workout_exercises(
        session,
        workout_id,
        user_id,
        limit=10,
        offset=5,
    )

    assert result is not None
    items, total = result

    ownership_statement = session.scalar.await_args_list[0].args[0]
    count_statement = session.scalar.await_args_list[1].args[0]
    items_statement = session.scalars.await_args.args[0]

    assert items == workout_exercises
    assert total == 2
    assert workout_id in ownership_statement.compile().params.values()
    assert user_id in ownership_statement.compile().params.values()
    assert workout_id in count_statement.compile().params.values()
    assert user_id in count_statement.compile().params.values()
    assert workout_id in items_statement.compile().params.values()
    assert user_id in items_statement.compile().params.values()
    assert "ORDER BY workout_exercises.position ASC" in str(items_statement)
    assert "workout_exercises.id ASC" in str(items_statement)
    assert 10 in items_statement.compile().params.values()
    assert 5 in items_statement.compile().params.values()


@pytest.mark.anyio
async def test_get_owned_workout_exercise_filters_parent_and_owner() -> None:
    workout_id = uuid4()
    workout_exercise_id = uuid4()
    user_id = uuid4()
    workout_exercise = SimpleNamespace(id=workout_exercise_id)
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=workout_exercise),
    )

    result = await get_owned_workout_exercise(
        session,
        workout_id,
        workout_exercise_id,
        user_id,
    )

    statement = session.scalar.await_args.args[0]
    parameters = statement.compile().params.values()

    assert result is workout_exercise
    assert workout_id in parameters
    assert workout_exercise_id in parameters
    assert user_id in parameters


@pytest.mark.anyio
async def test_update_workout_exercise_applies_patch_and_commits() -> None:
    old_exercise = make_exercise()
    new_exercise = make_exercise()
    workout_exercise = SimpleNamespace(
        exercise_id=old_exercise.id,
        exercise=old_exercise,
        position=1,
        rest_seconds=90,
        notes=None,
    )
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=new_exercise),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    result = await update_workout_exercise(
        session,
        workout_exercise,
        WorkoutExerciseUpdate(
            exercise_id=new_exercise.id,
            position=2,
            rest_seconds=None,
            notes="  Increased weight  ",
        ),
    )

    exercise_statement = session.scalar.await_args.args[0]

    assert result is workout_exercise
    assert workout_exercise.exercise_id == new_exercise.id
    assert workout_exercise.exercise is new_exercise
    assert workout_exercise.position == 2
    assert workout_exercise.rest_seconds is None
    assert workout_exercise.notes == "Increased weight"
    assert new_exercise.id in exercise_statement.compile().params.values()
    assert "exercises.is_active IS true" in str(exercise_statement)
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    assert session.refresh.await_args_list == [
        call(workout_exercise),
        call(workout_exercise, attribute_names=["exercise"]),
    ]


@pytest.mark.anyio
async def test_update_workout_exercise_requires_active_exercise() -> None:
    workout_exercise = SimpleNamespace(
        exercise_id=uuid4(),
        exercise=None,
        position=1,
        rest_seconds=None,
        notes=None,
    )
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=None),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    with pytest.raises(ActiveExerciseNotFoundError):
        await update_workout_exercise(
            session,
            workout_exercise,
            WorkoutExerciseUpdate(exercise_id=uuid4()),
        )

    session.commit.assert_not_awaited()
    session.refresh.assert_not_awaited()


@pytest.mark.anyio
async def test_update_workout_exercise_maps_position_conflict() -> None:
    database_error = SimpleNamespace(
        diag=SimpleNamespace(constraint_name="uq_workout_exercises_session_position")
    )
    integrity_error = IntegrityError(
        "UPDATE workout_exercises",
        {},
        database_error,
    )
    workout_exercise = SimpleNamespace(position=1)
    session = SimpleNamespace(
        commit=AsyncMock(side_effect=integrity_error),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    with pytest.raises(WorkoutExercisePositionConflictError):
        await update_workout_exercise(
            session,
            workout_exercise,
            WorkoutExerciseUpdate(position=2),
        )

    session.rollback.assert_awaited_once()
    session.refresh.assert_not_awaited()


@pytest.mark.anyio
async def test_delete_workout_exercise_rolls_back_database_errors() -> None:
    workout_exercise = SimpleNamespace(id=uuid4())
    session = SimpleNamespace(
        delete=AsyncMock(),
        commit=AsyncMock(side_effect=SQLAlchemyError("write failed")),
        rollback=AsyncMock(),
    )

    with pytest.raises(SQLAlchemyError, match="write failed"):
        await delete_workout_exercise(session, workout_exercise)

    session.delete.assert_awaited_once_with(workout_exercise)
    session.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_delete_workout_exercise_commits() -> None:
    workout_exercise = SimpleNamespace(id=uuid4())
    session = SimpleNamespace(
        delete=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    await delete_workout_exercise(session, workout_exercise)

    session.delete.assert_awaited_once_with(workout_exercise)
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
