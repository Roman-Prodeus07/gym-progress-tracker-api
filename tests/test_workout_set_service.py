from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.schemas import WorkoutSetCreate, WorkoutSetUpdate
from app.services import (
    WorkoutSetNumberConflictError,
    WorkoutSetPerformanceMetricRequiredError,
    create_workout_set,
    delete_workout_set,
    get_owned_workout_set,
    list_owned_workout_sets,
    update_workout_set,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_workout_set(
    *,
    set_number: int = 1,
    reps: int | None = 8,
    duration_seconds: int | None = None,
    distance_meters: Decimal | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        workout_exercise_id=uuid4(),
        set_number=set_number,
        set_type="working",
        reps=reps,
        weight_kg=Decimal("80.000"),
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        rpe=Decimal("8.0"),
        notes=None,
    )


@pytest.mark.anyio
async def test_create_workout_set_assigns_next_set_number() -> None:
    workout_id = uuid4()
    workout_exercise_id = uuid4()
    user_id = uuid4()
    workout_exercise = SimpleNamespace(id=workout_exercise_id)
    session = SimpleNamespace(
        scalar=AsyncMock(
            side_effect=[
                workout_exercise,
                3,
            ]
        ),
        add=Mock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    result = await create_workout_set(
        session,
        workout_id,
        workout_exercise_id,
        user_id,
        WorkoutSetCreate(
            reps=8,
            weight_kg="80.000",
            rpe="8.0",
        ),
    )

    ownership_statement = session.scalar.await_args_list[0].args[0]
    set_number_statement = session.scalar.await_args_list[1].args[0]
    ownership_parameters = ownership_statement.compile().params.values()

    assert result is not None
    assert result.workout_exercise_id == workout_exercise_id
    assert result.set_number == 3
    assert result.reps == 8
    assert result.weight_kg == Decimal("80.000")
    assert result.rpe == Decimal("8.0")

    assert workout_id in ownership_parameters
    assert workout_exercise_id in ownership_parameters
    assert user_id in ownership_parameters
    assert "FOR UPDATE" in str(ownership_statement)

    assert workout_exercise_id in (set_number_statement.compile().params.values())
    assert "max(workout_sets.set_number)" in str(set_number_statement)

    session.add.assert_called_once_with(result)
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    session.refresh.assert_awaited_once_with(result)


@pytest.mark.anyio
async def test_create_workout_set_uses_explicit_set_number() -> None:
    workout_exercise_id = uuid4()
    workout_exercise = SimpleNamespace(id=workout_exercise_id)
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=workout_exercise),
        add=Mock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    result = await create_workout_set(
        session,
        uuid4(),
        workout_exercise_id,
        uuid4(),
        WorkoutSetCreate(
            set_number=4,
            reps=6,
        ),
    )

    assert result is not None
    assert result.set_number == 4
    assert session.scalar.await_count == 1


@pytest.mark.anyio
async def test_create_workout_set_hides_unowned_parent() -> None:
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=None),
        add=Mock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    result = await create_workout_set(
        session,
        uuid4(),
        uuid4(),
        uuid4(),
        WorkoutSetCreate(reps=8),
    )

    assert result is None
    session.add.assert_not_called()
    session.commit.assert_not_awaited()
    session.refresh.assert_not_awaited()


@pytest.mark.anyio
async def test_create_workout_set_maps_set_number_conflict() -> None:
    database_error = SimpleNamespace(
        diag=SimpleNamespace(constraint_name="uq_workout_sets_exercise_set_number")
    )
    integrity_error = IntegrityError(
        "INSERT INTO workout_sets",
        {},
        database_error,
    )
    workout_exercise = SimpleNamespace(id=uuid4())
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=workout_exercise),
        add=Mock(),
        commit=AsyncMock(side_effect=integrity_error),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    with pytest.raises(WorkoutSetNumberConflictError):
        await create_workout_set(
            session,
            uuid4(),
            workout_exercise.id,
            uuid4(),
            WorkoutSetCreate(
                set_number=2,
                reps=8,
            ),
        )

    session.rollback.assert_awaited_once()
    session.refresh.assert_not_awaited()


@pytest.mark.anyio
async def test_list_owned_workout_sets_hides_unowned_parent() -> None:
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=None),
        scalars=AsyncMock(),
    )

    result = await list_owned_workout_sets(
        session,
        uuid4(),
        uuid4(),
        uuid4(),
        limit=20,
        offset=0,
    )

    assert result is None
    session.scalars.assert_not_awaited()


@pytest.mark.anyio
async def test_list_owned_workout_sets_filters_and_orders() -> None:
    workout_id = uuid4()
    workout_exercise_id = uuid4()
    user_id = uuid4()
    workout_sets = [
        make_workout_set(set_number=1),
        make_workout_set(set_number=2),
    ]
    scalar_result = SimpleNamespace(
        all=Mock(return_value=workout_sets),
    )
    session = SimpleNamespace(
        scalar=AsyncMock(
            side_effect=[
                workout_exercise_id,
                2,
            ]
        ),
        scalars=AsyncMock(return_value=scalar_result),
    )

    result = await list_owned_workout_sets(
        session,
        workout_id,
        workout_exercise_id,
        user_id,
        limit=10,
        offset=5,
    )

    assert result is not None
    items, total = result

    ownership_statement = session.scalar.await_args_list[0].args[0]
    count_statement = session.scalar.await_args_list[1].args[0]
    items_statement = session.scalars.await_args.args[0]

    assert items == workout_sets
    assert total == 2

    for statement in (
        ownership_statement,
        count_statement,
        items_statement,
    ):
        parameters = statement.compile().params.values()

        assert workout_id in parameters
        assert workout_exercise_id in parameters
        assert user_id in parameters

    assert "ORDER BY workout_sets.set_number ASC" in str(items_statement)
    assert "workout_sets.id ASC" in str(items_statement)
    assert 10 in items_statement.compile().params.values()
    assert 5 in items_statement.compile().params.values()


@pytest.mark.anyio
async def test_get_owned_workout_set_filters_full_parent_chain() -> None:
    workout_id = uuid4()
    workout_exercise_id = uuid4()
    workout_set_id = uuid4()
    user_id = uuid4()
    workout_set = make_workout_set()
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=workout_set),
    )

    result = await get_owned_workout_set(
        session,
        workout_id,
        workout_exercise_id,
        workout_set_id,
        user_id,
    )

    statement = session.scalar.await_args.args[0]
    parameters = statement.compile().params.values()

    assert result is workout_set
    assert workout_id in parameters
    assert workout_exercise_id in parameters
    assert workout_set_id in parameters
    assert user_id in parameters


@pytest.mark.anyio
async def test_update_workout_set_applies_patch_and_commits() -> None:
    workout_set = make_workout_set()
    session = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    result = await update_workout_set(
        session,
        workout_set,
        WorkoutSetUpdate(
            reps=10,
            weight_kg=None,
            rpe="9.0",
            notes="  Final working set  ",
        ),
    )

    assert result is workout_set
    assert workout_set.reps == 10
    assert workout_set.weight_kg is None
    assert workout_set.rpe == Decimal("9.0")
    assert workout_set.notes == "Final working set"
    assert workout_set.set_number == 1
    assert workout_set.set_type == "working"

    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    session.refresh.assert_awaited_once_with(workout_set)


@pytest.mark.anyio
async def test_update_workout_set_rejects_removing_last_metric() -> None:
    workout_set = make_workout_set(
        reps=8,
        duration_seconds=None,
        distance_meters=None,
    )
    session = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    with pytest.raises(WorkoutSetPerformanceMetricRequiredError):
        await update_workout_set(
            session,
            workout_set,
            WorkoutSetUpdate(reps=None),
        )

    assert workout_set.reps == 8
    session.commit.assert_not_awaited()
    session.refresh.assert_not_awaited()


@pytest.mark.anyio
async def test_update_workout_set_allows_replacing_last_metric() -> None:
    workout_set = make_workout_set(
        reps=8,
        duration_seconds=None,
        distance_meters=None,
    )
    session = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    result = await update_workout_set(
        session,
        workout_set,
        WorkoutSetUpdate(
            reps=None,
            duration_seconds=60,
        ),
    )

    assert result.reps is None
    assert result.duration_seconds == 60
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(workout_set)


@pytest.mark.anyio
async def test_update_workout_set_maps_set_number_conflict() -> None:
    database_error = SimpleNamespace(
        diag=SimpleNamespace(constraint_name="uq_workout_sets_exercise_set_number")
    )
    integrity_error = IntegrityError(
        "UPDATE workout_sets",
        {},
        database_error,
    )
    workout_set = make_workout_set()
    session = SimpleNamespace(
        commit=AsyncMock(side_effect=integrity_error),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    with pytest.raises(WorkoutSetNumberConflictError):
        await update_workout_set(
            session,
            workout_set,
            WorkoutSetUpdate(set_number=2),
        )

    session.rollback.assert_awaited_once()
    session.refresh.assert_not_awaited()


@pytest.mark.anyio
async def test_delete_workout_set_rolls_back_database_errors() -> None:
    workout_set = make_workout_set()
    session = SimpleNamespace(
        delete=AsyncMock(),
        commit=AsyncMock(side_effect=SQLAlchemyError("write failed")),
        rollback=AsyncMock(),
    )

    with pytest.raises(SQLAlchemyError, match="write failed"):
        await delete_workout_set(session, workout_set)

    session.delete.assert_awaited_once_with(workout_set)
    session.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_delete_workout_set_commits() -> None:
    workout_set = make_workout_set()
    session = SimpleNamespace(
        delete=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    await delete_workout_set(session, workout_set)

    session.delete.assert_awaited_once_with(workout_set)
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
