from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import workout_exercises as workout_exercise_routes
from app.db.session import get_db_session
from app.main import app
from app.schemas import WorkoutExerciseCreate, WorkoutExerciseUpdate
from app.services import (
    ActiveExerciseNotFoundError,
    WorkoutExercisePositionConflictError,
)


def make_exercise(
    name: str = "Bench Press",
    *,
    is_active: bool = True,
) -> SimpleNamespace:
    now = datetime.now(UTC)

    return SimpleNamespace(
        id=uuid4(),
        name=name,
        slug=name.lower().replace(" ", "-"),
        description=None,
        primary_muscle_group="chest",
        equipment="barbell",
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


def make_workout_exercise(
    workout_id: UUID,
    exercise: SimpleNamespace | None = None,
    *,
    position: int = 1,
) -> SimpleNamespace:
    now = datetime.now(UTC)
    exercise = exercise or make_exercise()

    return SimpleNamespace(
        id=uuid4(),
        workout_session_id=workout_id,
        exercise_id=exercise.id,
        exercise=exercise,
        position=position,
        rest_seconds=90,
        notes=None,
        created_at=now,
        updated_at=now,
    )


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


def test_create_workout_exercise_returns_owned_safe_response(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client
    workout_id = uuid4()
    exercise = make_exercise()
    workout_exercise = make_workout_exercise(
        workout_id,
        exercise,
        position=2,
    )

    async def fake_create_workout_exercise(
        session: object,
        requested_workout_id: UUID,
        user_id: UUID,
        workout_exercise_data: WorkoutExerciseCreate,
    ) -> SimpleNamespace:
        assert session is not None
        assert requested_workout_id == workout_id
        assert user_id == current_user.id
        assert workout_exercise_data.exercise_id == exercise.id
        assert workout_exercise_data.position == 2
        assert workout_exercise_data.notes == "Controlled repetitions"
        return workout_exercise

    monkeypatch.setattr(
        workout_exercise_routes,
        "create_workout_exercise_service",
        fake_create_workout_exercise,
    )

    response = client.post(
        f"/workouts/{workout_id}/exercises",
        json={
            "exercise_id": str(exercise.id),
            "position": 2,
            "rest_seconds": 90,
            "notes": "  Controlled repetitions  ",
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["id"] == str(workout_exercise.id)
    assert response_data["exercise_id"] == str(exercise.id)
    assert response_data["exercise"]["name"] == "Bench Press"
    assert response_data["position"] == 2
    assert "workout_session_id" not in response_data
    assert "is_active" not in response_data["exercise"]


def test_create_workout_exercise_hides_missing_or_unowned_workout(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = authenticated_client
    workout_id = uuid4()

    create_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(
        workout_exercise_routes,
        "create_workout_exercise_service",
        create_mock,
    )

    response = client.post(
        f"/workouts/{workout_id}/exercises",
        json={"exercise_id": str(uuid4())},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Workout not found."}
    create_mock.assert_awaited_once()


@pytest.mark.parametrize(
    ("error_type", "expected_status", "expected_detail"),
    [
        (
            ActiveExerciseNotFoundError,
            404,
            "Exercise not found.",
        ),
        (
            WorkoutExercisePositionConflictError,
            409,
            "Position is already used in this workout.",
        ),
    ],
)
def test_create_workout_exercise_maps_domain_errors(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[Exception],
    expected_status: int,
    expected_detail: str,
) -> None:
    client, _ = authenticated_client
    workout_id = uuid4()

    async def fake_create_workout_exercise(
        session: object,
        requested_workout_id: UUID,
        user_id: UUID,
        workout_exercise_data: WorkoutExerciseCreate,
    ) -> None:
        raise error_type

    monkeypatch.setattr(
        workout_exercise_routes,
        "create_workout_exercise_service",
        fake_create_workout_exercise,
    )

    response = client.post(
        f"/workouts/{workout_id}/exercises",
        json={"exercise_id": str(uuid4())},
    )

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


def test_list_workout_exercises_returns_owner_page(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client
    workout_id = uuid4()
    workout_exercises = [
        make_workout_exercise(
            workout_id,
            make_exercise("Bench Press"),
            position=1,
        ),
        make_workout_exercise(
            workout_id,
            make_exercise("Squat"),
            position=2,
        ),
    ]

    async def fake_list_workout_exercises(
        session: object,
        requested_workout_id: UUID,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[SimpleNamespace], int]:
        assert session is not None
        assert requested_workout_id == workout_id
        assert user_id == current_user.id
        assert limit == 10
        assert offset == 5
        return workout_exercises, 2

    monkeypatch.setattr(
        workout_exercise_routes,
        "list_owned_workout_exercises_service",
        fake_list_workout_exercises,
    )

    response = client.get(
        f"/workouts/{workout_id}/exercises",
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
    assert [item["position"] for item in response_data["items"]] == [1, 2]
    assert [item["exercise"]["name"] for item in response_data["items"]] == [
        "Bench Press",
        "Squat",
    ]


def test_list_workout_exercises_hides_missing_or_unowned_workout(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = authenticated_client
    workout_id = uuid4()

    list_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(
        workout_exercise_routes,
        "list_owned_workout_exercises_service",
        list_mock,
    )

    response = client.get(f"/workouts/{workout_id}/exercises")

    assert response.status_code == 404
    assert response.json() == {"detail": "Workout not found."}
    list_mock.assert_awaited_once()


def test_get_workout_exercise_returns_historical_inactive_exercise(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client
    workout_id = uuid4()
    exercise = make_exercise(is_active=False)
    workout_exercise = make_workout_exercise(workout_id, exercise)

    async def fake_get_workout_exercise(
        session: object,
        requested_workout_id: UUID,
        workout_exercise_id: UUID,
        user_id: UUID,
    ) -> SimpleNamespace:
        assert session is not None
        assert requested_workout_id == workout_id
        assert workout_exercise_id == workout_exercise.id
        assert user_id == current_user.id
        return workout_exercise

    monkeypatch.setattr(
        workout_exercise_routes,
        "get_owned_workout_exercise_service",
        fake_get_workout_exercise,
    )

    response = client.get(f"/workouts/{workout_id}/exercises/{workout_exercise.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(workout_exercise.id)
    assert response.json()["exercise"]["name"] == "Bench Press"
    assert "is_active" not in response.json()["exercise"]


@pytest.mark.parametrize(
    ("method", "request_body"),
    [
        ("GET", None),
        ("PATCH", {"position": 2}),
        ("DELETE", None),
    ],
)
def test_workout_exercise_item_endpoints_hide_missing_or_unowned_resource(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    request_body: dict[str, object] | None,
) -> None:
    client, _ = authenticated_client
    workout_id = uuid4()
    workout_exercise_id = uuid4()

    async def fake_get_workout_exercise(
        session: object,
        requested_workout_id: UUID,
        requested_workout_exercise_id: UUID,
        user_id: UUID,
    ) -> None:
        return None

    monkeypatch.setattr(
        workout_exercise_routes,
        "get_owned_workout_exercise_service",
        fake_get_workout_exercise,
    )

    path = f"/workouts/{workout_id}/exercises/{workout_exercise_id}"

    if request_body is None:
        response = client.request(method, path)
    else:
        response = client.request(
            method,
            path,
            json=request_body,
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Workout exercise not found."}


def test_update_workout_exercise_applies_patch(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client
    workout_id = uuid4()
    workout_exercise = make_workout_exercise(workout_id)

    async def fake_get_workout_exercise(
        session: object,
        requested_workout_id: UUID,
        workout_exercise_id: UUID,
        user_id: UUID,
    ) -> SimpleNamespace:
        assert requested_workout_id == workout_id
        assert workout_exercise_id == workout_exercise.id
        assert user_id == current_user.id
        return workout_exercise

    async def fake_update_workout_exercise(
        session: object,
        database_workout_exercise: SimpleNamespace,
        workout_exercise_data: WorkoutExerciseUpdate,
    ) -> SimpleNamespace:
        assert database_workout_exercise is workout_exercise
        assert workout_exercise_data.position == 2
        assert workout_exercise_data.rest_seconds is None
        assert workout_exercise_data.notes == "Heavier set"

        workout_exercise.position = workout_exercise_data.position
        workout_exercise.rest_seconds = workout_exercise_data.rest_seconds
        workout_exercise.notes = workout_exercise_data.notes
        workout_exercise.updated_at = datetime.now(UTC)
        return workout_exercise

    monkeypatch.setattr(
        workout_exercise_routes,
        "get_owned_workout_exercise_service",
        fake_get_workout_exercise,
    )
    monkeypatch.setattr(
        workout_exercise_routes,
        "update_workout_exercise_service",
        fake_update_workout_exercise,
    )

    response = client.patch(
        f"/workouts/{workout_id}/exercises/{workout_exercise.id}",
        json={
            "position": 2,
            "rest_seconds": None,
            "notes": "  Heavier set  ",
        },
    )

    assert response.status_code == 200
    assert response.json()["position"] == 2
    assert response.json()["rest_seconds"] is None
    assert response.json()["notes"] == "Heavier set"


@pytest.mark.parametrize(
    ("error_type", "expected_status", "expected_detail"),
    [
        (
            ActiveExerciseNotFoundError,
            404,
            "Exercise not found.",
        ),
        (
            WorkoutExercisePositionConflictError,
            409,
            "Position is already used in this workout.",
        ),
    ],
)
def test_update_workout_exercise_maps_domain_errors(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[Exception],
    expected_status: int,
    expected_detail: str,
) -> None:
    client, _ = authenticated_client
    workout_id = uuid4()
    workout_exercise = make_workout_exercise(workout_id)

    async def fake_get_workout_exercise(
        session: object,
        requested_workout_id: UUID,
        workout_exercise_id: UUID,
        user_id: UUID,
    ) -> SimpleNamespace:
        return workout_exercise

    async def fake_update_workout_exercise(
        session: object,
        database_workout_exercise: SimpleNamespace,
        workout_exercise_data: WorkoutExerciseUpdate,
    ) -> None:
        raise error_type

    monkeypatch.setattr(
        workout_exercise_routes,
        "get_owned_workout_exercise_service",
        fake_get_workout_exercise,
    )
    monkeypatch.setattr(
        workout_exercise_routes,
        "update_workout_exercise_service",
        fake_update_workout_exercise,
    )

    response = client.patch(
        f"/workouts/{workout_id}/exercises/{workout_exercise.id}",
        json={"position": 2},
    )

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


def test_delete_workout_exercise_returns_no_content(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = authenticated_client
    workout_id = uuid4()
    workout_exercise = make_workout_exercise(workout_id)

    async def fake_get_workout_exercise(
        session: object,
        requested_workout_id: UUID,
        workout_exercise_id: UUID,
        user_id: UUID,
    ) -> SimpleNamespace:
        return workout_exercise

    delete_mock = AsyncMock()

    monkeypatch.setattr(
        workout_exercise_routes,
        "get_owned_workout_exercise_service",
        fake_get_workout_exercise,
    )
    monkeypatch.setattr(
        workout_exercise_routes,
        "delete_workout_exercise_service",
        delete_mock,
    )

    response = client.delete(f"/workouts/{workout_id}/exercises/{workout_exercise.id}")

    assert response.status_code == 204
    assert response.content == b""
    delete_mock.assert_awaited_once_with(
        ANY,
        workout_exercise,
    )


@pytest.mark.parametrize(
    ("method", "path", "request_body"),
    [
        (
            "POST",
            f"/workouts/{uuid4()}/exercises",
            {"exercise_id": str(uuid4())},
        ),
        ("GET", f"/workouts/{uuid4()}/exercises", None),
        (
            "GET",
            f"/workouts/{uuid4()}/exercises/{uuid4()}",
            None,
        ),
        (
            "PATCH",
            f"/workouts/{uuid4()}/exercises/{uuid4()}",
            {"position": 2},
        ),
        (
            "DELETE",
            f"/workouts/{uuid4()}/exercises/{uuid4()}",
            None,
        ),
    ],
)
def test_workout_exercise_endpoints_require_authentication(
    method: str,
    path: str,
    request_body: dict[str, object] | None,
) -> None:
    with TestClient(app) as client:
        response = client.request(
            method,
            path,
            json=request_body,
        )

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
def test_list_workout_exercises_rejects_invalid_pagination(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
    query_parameters: dict[str, int],
    invalid_field: str,
) -> None:
    client, _ = authenticated_client
    list_mock = AsyncMock()

    monkeypatch.setattr(
        workout_exercise_routes,
        "list_owned_workout_exercises_service",
        list_mock,
    )

    response = client.get(
        f"/workouts/{uuid4()}/exercises",
        params=query_parameters,
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == invalid_field
    list_mock.assert_not_awaited()


def test_workout_exercise_openapi_documents_security_and_responses() -> None:
    schema = app.openapi()
    collection_operations = schema["paths"]["/workouts/{workout_id}/exercises"]
    item_operations = schema["paths"][
        "/workouts/{workout_id}/exercises/{workout_exercise_id}"
    ]
    operations = [
        collection_operations["get"],
        collection_operations["post"],
        item_operations["get"],
        item_operations["patch"],
        item_operations["delete"],
    ]

    for operation in operations:
        assert operation["security"] == [{"OAuth2PasswordBearer": []}]
        assert "401" in operation["responses"]

    assert "201" in collection_operations["post"]["responses"]
    assert "404" in collection_operations["post"]["responses"]
    assert "409" in collection_operations["post"]["responses"]
    assert "404" in collection_operations["get"]["responses"]
    assert "404" in item_operations["get"]["responses"]
    assert "404" in item_operations["patch"]["responses"]
    assert "409" in item_operations["patch"]["responses"]
    assert "204" in item_operations["delete"]["responses"]
    assert "404" in item_operations["delete"]["responses"]

    response_properties = schema["components"]["schemas"]["WorkoutExerciseResponse"][
        "properties"
    ]
    exercise_properties = schema["components"]["schemas"]["ExerciseResponse"][
        "properties"
    ]

    assert "workout_session_id" not in response_properties
    assert "is_active" not in exercise_properties
