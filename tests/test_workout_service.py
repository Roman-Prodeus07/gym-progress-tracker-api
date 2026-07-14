from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.schemas import WorkoutSessionCreate, WorkoutSessionUpdate
from app.services import (
    InvalidWorkoutTimeRangeError,
    create_workout_session,
    delete_workout_session,
    get_owned_workout_session,
    list_workout_sessions,
    update_workout_session,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_create_workout_session_assigns_owner_and_commits() -> None:
    user_id = uuid4()
    started_at = datetime.now(UTC)
    session = SimpleNamespace(
        add=Mock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    workout = await create_workout_session(
        session,
        user_id,
        WorkoutSessionCreate(
            name="Push Day",
            notes="Heavy session",
            started_at=started_at,
        ),
    )

    assert workout.user_id == user_id
    assert workout.name == "Push Day"
    assert workout.started_at == started_at
    session.add.assert_called_once_with(workout)
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    session.refresh.assert_awaited_once_with(workout)


@pytest.mark.anyio
async def test_create_workout_session_rolls_back_database_errors() -> None:
    session = SimpleNamespace(
        add=Mock(),
        commit=AsyncMock(side_effect=SQLAlchemyError("write failed")),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    with pytest.raises(SQLAlchemyError, match="write failed"):
        await create_workout_session(
            session,
            uuid4(),
            WorkoutSessionCreate(name="Push Day"),
        )

    session.rollback.assert_awaited_once()
    session.refresh.assert_not_awaited()


@pytest.mark.anyio
async def test_list_workout_sessions_filters_owner_and_paginates() -> None:
    user_id = uuid4()
    workouts = [SimpleNamespace(id=uuid4())]
    scalar_result = SimpleNamespace(
        all=Mock(return_value=workouts),
    )
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=1),
        scalars=AsyncMock(return_value=scalar_result),
    )

    result, total = await list_workout_sessions(
        session,
        user_id,
        limit=20,
        offset=5,
    )

    count_statement = session.scalar.await_args.args[0]
    items_statement = session.scalars.await_args.args[0]
    count_parameters = count_statement.compile().params.values()
    items_parameters = items_statement.compile().params.values()

    assert result == workouts
    assert total == 1
    assert user_id in count_parameters
    assert user_id in items_parameters
    assert 20 in items_parameters
    assert 5 in items_parameters
    assert "ORDER BY workout_sessions.started_at DESC" in str(items_statement)
    assert "workout_sessions.created_at DESC" in str(items_statement)
    assert "workout_sessions.id DESC" in str(items_statement)


@pytest.mark.anyio
async def test_get_owned_workout_session_filters_id_and_owner() -> None:
    workout_id = uuid4()
    user_id = uuid4()
    workout = SimpleNamespace(id=workout_id, user_id=user_id)
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=workout),
    )

    result = await get_owned_workout_session(
        session,
        workout_id,
        user_id,
    )

    statement = session.scalar.await_args.args[0]
    statement_parameters = statement.compile().params.values()

    assert result is workout
    assert workout_id in statement_parameters
    assert user_id in statement_parameters


@pytest.mark.anyio
async def test_update_workout_session_applies_patch_and_commits() -> None:
    started_at = datetime.now(UTC)
    completed_at = started_at + timedelta(hours=1)
    workout = SimpleNamespace(
        name="Old name",
        notes="Old notes",
        started_at=started_at,
        completed_at=None,
    )
    session = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    result = await update_workout_session(
        session,
        workout,
        WorkoutSessionUpdate(
            name="  Upper Body  ",
            notes=None,
            completed_at=completed_at,
        ),
    )

    assert result is workout
    assert workout.name == "Upper Body"
    assert workout.notes is None
    assert workout.completed_at == completed_at
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    session.refresh.assert_awaited_once_with(workout)


@pytest.mark.anyio
async def test_update_workout_session_rejects_partial_invalid_time_range() -> None:
    started_at = datetime.now(UTC)
    workout = SimpleNamespace(
        name="Push Day",
        notes=None,
        started_at=started_at,
        completed_at=started_at + timedelta(hours=1),
    )
    session = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    with pytest.raises(InvalidWorkoutTimeRangeError):
        await update_workout_session(
            session,
            workout,
            WorkoutSessionUpdate(
                started_at=started_at + timedelta(hours=2),
            ),
        )

    session.commit.assert_not_awaited()
    session.refresh.assert_not_awaited()


@pytest.mark.anyio
async def test_delete_workout_session_commits() -> None:
    workout = SimpleNamespace(id=uuid4())
    session = SimpleNamespace(
        delete=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    await delete_workout_session(session, workout)

    session.delete.assert_awaited_once_with(workout)
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
