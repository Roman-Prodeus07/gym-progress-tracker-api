from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import progress as progress_routes
from app.db.session import get_db_session
from app.main import app
from app.schemas import PersonalRecordResponse, PersonalRecordType


@pytest.fixture
def authenticated_client() -> Iterator[tuple[TestClient, SimpleNamespace]]:
    current_user = SimpleNamespace(id=uuid4())

    async def override_get_db_session() -> AsyncGenerator[object]:
        yield object()

    async def override_get_current_user() -> SimpleNamespace:
        return current_user

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        with TestClient(app) as client:
            yield client, current_user
    finally:
        app.dependency_overrides.clear()


def test_list_personal_records_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/progress/personal-records")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_list_personal_records_returns_owner_page(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client

    record = PersonalRecordResponse(
        exercise_id=uuid4(),
        exercise_name="Bench Press",
        record_type=PersonalRecordType.MAX_WEIGHT,
        value=Decimal("100.000"),
        workout_id=uuid4(),
        workout_exercise_id=uuid4(),
        workout_set_id=uuid4(),
        achieved_at=datetime(2026, 8, 1, 10, 30, tzinfo=UTC),
        reps=5,
        weight_kg=Decimal("100.000"),
        duration_seconds=None,
        distance_meters=None,
    )

    list_service = AsyncMock(return_value=([record], 1))

    monkeypatch.setattr(
        progress_routes,
        "list_personal_records_service",
        list_service,
    )

    response = client.get(
        "/progress/personal-records",
        params={
            "limit": 25,
            "offset": 5,
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["total"] == 1
    assert response_data["limit"] == 25
    assert response_data["offset"] == 5
    assert len(response_data["items"]) == 1
    assert response_data["items"][0]["exercise_id"] == str(record.exercise_id)
    assert response_data["items"][0]["exercise_name"] == "Bench Press"
    assert response_data["items"][0]["record_type"] == "max_weight"

    list_service.assert_awaited_once_with(
        ANY,
        current_user.id,
        25,
        5,
    )
