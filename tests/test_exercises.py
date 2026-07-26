from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import exercises as exercise_routes
from app.db.session import get_db_session
from app.main import app


def make_exercise(name: str = "Bench Press") -> SimpleNamespace:
    now = datetime.now(UTC)

    return SimpleNamespace(
        id=uuid4(),
        name=name,
        slug=name.lower().replace(" ", "-"),
        description=None,
        primary_muscle_group="chest",
        equipment="barbell",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def authenticated_client() -> Iterator[TestClient]:
    current_user = SimpleNamespace(id=uuid4())

    async def override_get_db_session() -> AsyncGenerator[object]:
        yield object()

    async def override_get_current_user() -> SimpleNamespace:
        return current_user

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_list_exercises_returns_active_catalogue_page(
    authenticated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exercises = [
        make_exercise("Bench Press"),
        make_exercise("Squat"),
    ]

    async def fake_list_active_exercises(
        session: object,
        limit: int,
        offset: int,
    ) -> tuple[list[SimpleNamespace], int]:
        assert session is not None
        assert limit == 10
        assert offset == 5
        return exercises, 2

    monkeypatch.setattr(
        exercise_routes,
        "list_active_exercises_service",
        fake_list_active_exercises,
    )

    response = authenticated_client.get(
        "/exercises",
        params={
            "limit": 10,
            "offset": 5,
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["total"] == 2
    assert response_data["limit"] == 10
    assert response_data["offset"] == 5
    assert [item["name"] for item in response_data["items"]] == [
        "Bench Press",
        "Squat",
    ]
    assert "is_active" not in response_data["items"][0]


def test_get_exercise_returns_catalogue_exercise(
    authenticated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exercise = make_exercise()

    async def fake_get_active_exercise(
        session: object,
        exercise_id: UUID,
    ) -> SimpleNamespace:
        assert session is not None
        assert exercise_id == exercise.id
        return exercise

    monkeypatch.setattr(
        exercise_routes,
        "get_active_exercise_service",
        fake_get_active_exercise,
    )

    response = authenticated_client.get(f"/exercises/{exercise.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(exercise.id)
    assert response.json()["name"] == "Bench Press"


def test_get_exercise_hides_missing_or_inactive_exercise(
    authenticated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exercise_id = uuid4()

    async def fake_get_active_exercise(
        session: object,
        exercise_id: UUID,
    ) -> None:
        return None

    monkeypatch.setattr(
        exercise_routes,
        "get_active_exercise_service",
        fake_get_active_exercise,
    )

    response = authenticated_client.get(f"/exercises/{exercise_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Exercise not found."}


@pytest.mark.parametrize(
    "path",
    [
        "/exercises",
        f"/exercises/{uuid4()}",
    ],
)
def test_exercise_endpoints_require_authentication(path: str) -> None:
    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    ("query_parameters", "invalid_field"),
    [
        ({"limit": 0}, "limit"),
        ({"limit": 101}, "limit"),
        ({"offset": -1}, "offset"),
    ],
)
def test_list_exercises_rejects_invalid_pagination(
    authenticated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    query_parameters: dict[str, int],
    invalid_field: str,
) -> None:
    list_mock = AsyncMock()

    monkeypatch.setattr(
        exercise_routes,
        "list_active_exercises_service",
        list_mock,
    )

    response = authenticated_client.get(
        "/exercises",
        params=query_parameters,
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == invalid_field
    list_mock.assert_not_awaited()


def test_exercise_openapi_documents_security_and_responses() -> None:
    schema = app.openapi()
    collection_operation = schema["paths"]["/exercises"]["get"]
    item_operation = schema["paths"]["/exercises/{exercise_id}"]["get"]

    for operation in [collection_operation, item_operation]:
        assert operation["security"] == [{"OAuth2PasswordBearer": []}]
        assert "401" in operation["responses"]

    assert "404" in item_operation["responses"]

    response_properties = schema["components"]["schemas"]["ExerciseResponse"][
        "properties"
    ]

    assert "is_active" not in response_properties
