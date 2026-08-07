from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import workouts as workout_routes
from app.db.session import get_db_session
from app.main import app
from app.schemas import WorkoutSessionCreate, WorkoutSessionUpdate
from app.services import InvalidWorkoutTimeRangeError


def make_workout(
    user_id: UUID,
    name: str = "Push Day",
) -> SimpleNamespace:
    now = datetime.now(UTC)

    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        name=name,
        notes=None,
        started_at=now,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )


def make_workout_detail(
    user_id: UUID,
) -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace]:
    workout = make_workout(user_id)
    now = workout.created_at

    exercise = SimpleNamespace(
        id=uuid4(),
        name="Bench Press",
        slug="bench-press",
        description="Chest compound exercise.",
        primary_muscle_group="chest",
        equipment="barbell",
        created_at=now,
        updated_at=now,
    )
    workout_set = SimpleNamespace(
        id=uuid4(),
        set_number=1,
        set_type="working",
        reps=10,
        weight_kg=None,
        duration_seconds=None,
        distance_meters=None,
        rpe=None,
        notes=None,
        created_at=now,
        updated_at=now,
    )
    workout_exercise = SimpleNamespace(
        id=uuid4(),
        exercise_id=exercise.id,
        exercise=exercise,
        position=1,
        rest_seconds=120,
        notes=None,
        created_at=now,
        updated_at=now,
        workout_sets=[workout_set],
    )

    workout.workout_exercises = [workout_exercise]

    return workout, workout_exercise, workout_set


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


def test_create_workout_returns_owned_safe_response(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client
    workout = make_workout(current_user.id)

    async def fake_create_workout(
        session: object,
        user_id: UUID,
        workout_data: WorkoutSessionCreate,
    ) -> SimpleNamespace:
        assert session is not None
        assert user_id == current_user.id
        assert workout_data.name == "Push Day"
        return workout

    monkeypatch.setattr(
        workout_routes,
        "create_workout_session_service",
        fake_create_workout,
    )

    response = client.post(
        "/workouts",
        json={
            "name": "  Push Day  ",
            "notes": None,
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["id"] == str(workout.id)
    assert response_data["name"] == "Push Day"
    assert "user_id" not in response_data
    assert set(response_data) == {
        "id",
        "name",
        "notes",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    }


def test_list_workouts_returns_owner_page(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client
    workouts = [
        make_workout(current_user.id, "Pull Day"),
        make_workout(current_user.id, "Push Day"),
    ]

    async def fake_list_workouts(
        session: object,
        user_id: UUID,
        limit: int,
        offset: int,
        *,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
    ) -> tuple[list[SimpleNamespace], int]:
        assert session is not None
        assert user_id == current_user.id
        assert limit == 10
        assert offset == 5
        assert started_from is None
        assert started_to is None
        return workouts, 2

    monkeypatch.setattr(
        workout_routes,
        "list_workout_sessions_service",
        fake_list_workouts,
    )

    response = client.get(
        "/workouts",
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
        "Pull Day",
        "Push Day",
    ]


def test_list_workouts_forwards_started_at_range(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client
    expected_started_from = datetime(2026, 7, 1, tzinfo=UTC)
    expected_started_to = datetime(2026, 7, 31, 23, 59, 59, tzinfo=UTC)

    async def fake_list_workouts(
        session: object,
        user_id: UUID,
        limit: int,
        offset: int,
        *,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
    ) -> tuple[list[SimpleNamespace], int]:
        assert session is not None
        assert user_id == current_user.id
        assert limit == 20
        assert offset == 0
        assert started_from == expected_started_from
        assert started_to == expected_started_to
        return [], 0

    monkeypatch.setattr(
        workout_routes,
        "list_workout_sessions_service",
        fake_list_workouts,
    )

    response = client.get(
        "/workouts",
        params={
            "started_from": expected_started_from.isoformat(),
            "started_to": expected_started_to.isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
    }


def test_list_workouts_rejects_reversed_started_at_range(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = authenticated_client
    list_service = AsyncMock()

    monkeypatch.setattr(
        workout_routes,
        "list_workout_sessions_service",
        list_service,
    )

    response = client.get(
        "/workouts",
        params={
            "started_from": "2026-07-31T00:00:00Z",
            "started_to": "2026-07-01T00:00:00Z",
        },
    )

    assert response.status_code == 422
    assert "started_to cannot be earlier than started_from." in response.text
    list_service.assert_not_awaited()


@pytest.mark.parametrize(
    "parameter_name",
    ["started_from", "started_to"],
)
def test_list_workouts_rejects_timezone_naive_started_at_filter(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
    parameter_name: str,
) -> None:
    client, _ = authenticated_client
    list_service = AsyncMock()

    monkeypatch.setattr(
        workout_routes,
        "list_workout_sessions_service",
        list_service,
    )

    response = client.get(
        "/workouts",
        params={parameter_name: "2026-07-01T12:00:00"},
    )

    assert response.status_code == 422
    list_service.assert_not_awaited()


def test_list_workouts_accepts_equal_started_at_bounds(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = authenticated_client
    expected_timestamp = datetime(2026, 7, 1, 12, tzinfo=UTC)
    list_service = AsyncMock(return_value=([], 0))

    monkeypatch.setattr(
        workout_routes,
        "list_workout_sessions_service",
        list_service,
    )

    response = client.get(
        "/workouts",
        params={
            "started_from": expected_timestamp.isoformat(),
            "started_to": expected_timestamp.isoformat(),
        },
    )

    assert response.status_code == 200
    assert list_service.await_args.kwargs == {
        "started_from": expected_timestamp,
        "started_to": expected_timestamp,
    }


def test_get_workout_returns_owned_workout_detail(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client
    workout, workout_exercise, workout_set = make_workout_detail(current_user.id)

    async def fake_get_owned_workout_detail(
        session: object,
        workout_id: UUID,
        user_id: UUID,
    ) -> SimpleNamespace:
        assert session is not None
        assert workout_id == workout.id
        assert user_id == current_user.id
        return workout

    monkeypatch.setattr(
        workout_routes,
        "get_owned_workout_session_detail_service",
        fake_get_owned_workout_detail,
    )

    response = client.get(f"/workouts/{workout.id}")

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == str(workout.id)
    assert len(response_data["exercises"]) == 1

    exercise_data = response_data["exercises"][0]

    assert exercise_data["id"] == str(workout_exercise.id)
    assert exercise_data["position"] == 1
    assert exercise_data["exercise"]["name"] == "Bench Press"
    assert exercise_data["exercise"]["slug"] == "bench-press"
    assert len(exercise_data["sets"]) == 1

    set_data = exercise_data["sets"][0]

    assert set_data["id"] == str(workout_set.id)
    assert set_data["set_number"] == 1
    assert set_data["set_type"] == "working"
    assert set_data["reps"] == 10


@pytest.mark.parametrize(
    ("method", "request_body"),
    [
        ("GET", None),
        ("PATCH", {"name": "Changed name"}),
        ("DELETE", None),
    ],
)
def test_workout_endpoints_hide_missing_or_unowned_workout(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    request_body: dict[str, object] | None,
) -> None:
    client, _ = authenticated_client
    workout_id = uuid4()

    async def fake_get_owned_workout(
        session: object,
        workout_id: UUID,
        user_id: UUID,
    ) -> None:
        return None

    monkeypatch.setattr(
        workout_routes,
        "get_owned_workout_session_service",
        fake_get_owned_workout,
    )
    monkeypatch.setattr(
        workout_routes,
        "get_owned_workout_session_detail_service",
        fake_get_owned_workout,
    )

    if request_body is None:
        response = client.request(
            method,
            f"/workouts/{workout_id}",
        )
    else:
        response = client.request(
            method,
            f"/workouts/{workout_id}",
            json=request_body,
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Workout not found."}


def test_update_workout_applies_patch(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client
    workout = make_workout(current_user.id)

    async def fake_get_owned_workout(
        session: object,
        workout_id: UUID,
        user_id: UUID,
    ) -> SimpleNamespace:
        return workout

    async def fake_update_workout(
        session: object,
        database_workout: SimpleNamespace,
        workout_data: WorkoutSessionUpdate,
    ) -> SimpleNamespace:
        assert database_workout is workout
        assert workout_data.name == "Upper Body"
        assert workout_data.notes is None

        workout.name = workout_data.name
        workout.notes = workout_data.notes
        workout.updated_at = datetime.now(UTC)
        return workout

    monkeypatch.setattr(
        workout_routes,
        "get_owned_workout_session_service",
        fake_get_owned_workout,
    )
    monkeypatch.setattr(
        workout_routes,
        "update_workout_session_service",
        fake_update_workout,
    )

    response = client.patch(
        f"/workouts/{workout.id}",
        json={
            "name": "  Upper Body  ",
            "notes": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Upper Body"
    assert response.json()["notes"] is None


def test_update_workout_maps_invalid_time_range_to_422(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client
    workout = make_workout(current_user.id)

    async def fake_get_owned_workout(
        session: object,
        workout_id: UUID,
        user_id: UUID,
    ) -> SimpleNamespace:
        return workout

    async def fake_update_workout(
        session: object,
        database_workout: SimpleNamespace,
        workout_data: WorkoutSessionUpdate,
    ) -> None:
        raise InvalidWorkoutTimeRangeError

    monkeypatch.setattr(
        workout_routes,
        "get_owned_workout_session_service",
        fake_get_owned_workout,
    )
    monkeypatch.setattr(
        workout_routes,
        "update_workout_session_service",
        fake_update_workout,
    )

    response = client.patch(
        f"/workouts/{workout.id}",
        json={
            "completed_at": "2026-07-14T08:00:00Z",
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "completed_at cannot be earlier than started_at."
    }


def test_delete_workout_returns_no_content(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client
    workout = make_workout(current_user.id)

    async def fake_get_owned_workout(
        session: object,
        workout_id: UUID,
        user_id: UUID,
    ) -> SimpleNamespace:
        return workout

    delete_mock = AsyncMock()

    monkeypatch.setattr(
        workout_routes,
        "get_owned_workout_session_service",
        fake_get_owned_workout,
    )
    monkeypatch.setattr(
        workout_routes,
        "delete_workout_session_service",
        delete_mock,
    )

    response = client.delete(f"/workouts/{workout.id}")

    assert response.status_code == 204
    assert response.content == b""
    delete_mock.assert_awaited_once_with(
        ANY,
        workout,
    )


def test_workouts_require_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/workouts")

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
def test_list_workouts_rejects_invalid_pagination(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
    query_parameters: dict[str, int],
    invalid_field: str,
) -> None:
    client, _ = authenticated_client
    list_mock = AsyncMock()

    monkeypatch.setattr(
        workout_routes,
        "list_workout_sessions_service",
        list_mock,
    )

    response = client.get(
        "/workouts",
        params=query_parameters,
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == invalid_field
    list_mock.assert_not_awaited()


def test_workout_openapi_documents_security_and_responses() -> None:
    schema = app.openapi()
    collection_operations = schema["paths"]["/workouts"]
    item_operations = schema["paths"]["/workouts/{workout_id}"]
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
    assert "404" in item_operations["get"]["responses"]
    assert "404" in item_operations["patch"]["responses"]
    assert "204" in item_operations["delete"]["responses"]

    get_response_schema = item_operations["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]

    assert get_response_schema == {
        "$ref": "#/components/schemas/WorkoutSessionDetailResponse"
    }

    detail_response_properties = schema["components"]["schemas"][
        "WorkoutSessionDetailResponse"
    ]["properties"]
    workout_exercise_detail_properties = schema["components"]["schemas"][
        "WorkoutExerciseDetailResponse"
    ]["properties"]

    assert "exercises" in detail_response_properties
    assert "sets" in workout_exercise_detail_properties

    response_properties = schema["components"]["schemas"]["WorkoutSessionResponse"][
        "properties"
    ]

    assert "user_id" not in response_properties
