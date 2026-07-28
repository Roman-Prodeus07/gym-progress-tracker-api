from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.services.exercise_seed import (
    EXERCISE_SEEDS,
    seed_exercise_catalogue,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_exercise_seed_data_is_valid_and_unique() -> None:
    slugs = [exercise["slug"] for exercise in EXERCISE_SEEDS]
    names = [exercise["name"] for exercise in EXERCISE_SEEDS]

    assert len(EXERCISE_SEEDS) == 20
    assert len(slugs) == len(set(slugs))
    assert len(names) == len(set(names))
    assert all(slug == slug.lower() for slug in slugs)
    assert all(" " not in slug for slug in slugs)


@pytest.mark.anyio
async def test_seed_exercise_catalogue_uses_conflict_safe_insert() -> None:
    inserted_ids = [uuid4(), uuid4()]
    scalar_result = SimpleNamespace(
        all=Mock(return_value=inserted_ids),
    )
    session = SimpleNamespace(
        scalars=AsyncMock(return_value=scalar_result),
        commit=AsyncMock(),
    )

    inserted_count = await seed_exercise_catalogue(session)

    statement = session.scalars.await_args.args[0]
    compiled_statement = " ".join(
        str(
            statement.compile(
                dialect=postgresql.dialect(),
            )
        ).split()
    )

    assert inserted_count == 2
    assert "ON CONFLICT (slug) DO NOTHING" in compiled_statement
    assert "RETURNING exercises.id" in compiled_statement
    session.commit.assert_awaited_once_with()


@pytest.mark.anyio
async def test_seed_exercise_catalogue_reports_existing_rows() -> None:
    scalar_result = SimpleNamespace(
        all=Mock(return_value=[]),
    )
    session = SimpleNamespace(
        scalars=AsyncMock(return_value=scalar_result),
        commit=AsyncMock(),
    )

    inserted_count = await seed_exercise_catalogue(session)

    assert inserted_count == 0
    session.commit.assert_awaited_once_with()
