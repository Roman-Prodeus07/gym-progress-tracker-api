from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.services import get_active_exercise, list_active_exercises


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_list_active_exercises_filters_orders_and_paginates() -> None:
    exercises = [
        SimpleNamespace(id=uuid4(), name="Bench Press"),
        SimpleNamespace(id=uuid4(), name="Squat"),
    ]
    scalar_result = SimpleNamespace(
        all=Mock(return_value=exercises),
    )
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=2),
        scalars=AsyncMock(return_value=scalar_result),
    )

    result, total = await list_active_exercises(
        session,
        limit=20,
        offset=5,
    )

    count_statement = session.scalar.await_args.args[0]
    items_statement = session.scalars.await_args.args[0]
    items_parameters = items_statement.compile().params.values()

    assert result == exercises
    assert total == 2
    assert "exercises.is_active IS true" in str(count_statement)
    assert "exercises.is_active IS true" in str(items_statement)
    assert "ORDER BY exercises.name ASC, exercises.id ASC" in str(items_statement)
    assert 20 in items_parameters
    assert 5 in items_parameters


@pytest.mark.anyio
async def test_get_active_exercise_filters_id_and_active_status() -> None:
    exercise_id = uuid4()
    exercise = SimpleNamespace(id=exercise_id, is_active=True)
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=exercise),
    )

    result = await get_active_exercise(
        session,
        exercise_id,
    )

    statement = session.scalar.await_args.args[0]
    statement_parameters = statement.compile().params.values()

    assert result is exercise
    assert exercise_id in statement_parameters
    assert "exercises.is_active IS true" in str(statement)
