from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import workout_sets as workout_set_routes
from app.db.session import get_db_session
from app.main import app
from app.schemas import WorkoutSetCreate, WorkoutSetUpdate
from app.services import (
    WorkoutSetNumberConflictError,
    WorkoutSetPerformanceMetricRequiredError,
)


def make_workout_set(
    workout_exercise_id: UUID,
    *,
    set_number: int = 1,
    reps: int | None = 8,
    duration_seconds: int | None = None,
    distance_meters: Decimal | None = None,
) -> SimpleNamespace:
    now = datetime.now(UTC)

    return SimpleNamespace(
        id=uuid4(),
        workout_exercise_id=workout_exercise_id,
        set_number=set_number,
        set_type="working",
        reps=reps,
        weight_kg=Decimal("80.000"),
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        rpe=Decimal("8.5"),
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


def test_create_workout_set_returns_safe_response(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client
    workout_id = uuid4()
    workout_exercise_id = uuid4()
    workout_set = make_workout_set(workout_exercise_id)

    async def fake_create_workout_set(
        session: object,
        requested_workout_id: UUID,
        requested_workout_exercise_id: UUID,
        user_id: UUID,
        workout_set_data: WorkoutSetCreate,
    ) -> SimpleNamespace:
        assert session is not None
        assert requested_workout_id == workout_id
        assert requested_workout_exercise_id == workout_exercise_id
        assert user_id == current_user.id
        assert workout_set_data.reps == 8
        assert workout_set_data.weight_kg == Decimal("80.000")
        assert workout_set_data.rpe == Decimal("8.5")
        assert workout_set_data.notes == "Top set"

        return workout_set

    monkeypatch.setattr(
        workout_set_routes,
        "create_workout_set_service",
        fake_create_workout_set,
    )

    response = client.post(
        (f"/workouts/{workout_id}/exercises/{workout_exercise_id}/sets"),
        json={
            "set_number": 1,
            "set_type": "working",
            "reps": 8,
            "weight_kg": "80.000",
            "rpe": "8.5",
            "notes": "  Top set  ",
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["id"] == str(workout_set.id)
    assert response_data["set_number"] == 1
    assert response_data["reps"] == 8
    assert response_data["weight_kg"] == "80.000"
    assert response_data["notes"] is None
    assert "workout_exercise_id" not in response_data
    assert set(response_data) == {
        "id",
        "set_number",
        "set_type",
        "reps",
        "weight_kg",
        "duration_seconds",
        "distance_meters",
        "rpe",
        "notes",
        "created_at",
        "updated_at",
    }


def test_create_workout_set_hides_missing_or_unowned_parent(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = authenticated_client
    workout_id = uuid4()
    workout_exercise_id = uuid4()

    async def fake_create_workout_set(
        _session: object,
        _workout_id: UUID,
        _workout_exercise_id: UUID,
        _user_id: UUID,
        _workout_set_data: WorkoutSetCreate,
    ) -> None:
        return None

    monkeypatch.setattr(
        workout_set_routes,
        "create_workout_set_service",
        fake_create_workout_set,
    )

    response = client.post(
        (f"/workouts/{workout_id}/exercises/{workout_exercise_id}/sets"),
        json={"reps": 8},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Workout exercise not found.",
    }


def test_create_workout_set_maps_set_number_conflict(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = authenticated_client
    workout_id = uuid4()
    workout_exercise_id = uuid4()

    async def fake_create_workout_set(
        _session: object,
        _workout_id: UUID,
        _workout_exercise_id: UUID,
        _user_id: UUID,
        _workout_set_data: WorkoutSetCreate,
    ) -> None:
        raise WorkoutSetNumberConflictError

    monkeypatch.setattr(
        workout_set_routes,
        "create_workout_set_service",
        fake_create_workout_set,
    )

    response = client.post(
        (f"/workouts/{workout_id}/exercises/{workout_exercise_id}/sets"),
        json={
            "set_number": 2,
            "reps": 8,
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": ("Set number is already used for this workout exercise."),
    }


def test_create_workout_set_rejects_missing_performance_metric(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = authenticated_client
    create_mock = AsyncMock()

    monkeypatch.setattr(
        workout_set_routes,
        "create_workout_set_service",
        create_mock,
    )

    response = client.post(
        (f"/workouts/{uuid4()}/exercises/{uuid4()}/sets"),
        json={"set_number": 1},
    )

    assert response.status_code == 422
    assert (
        "At least one performance metric must be provided"
        in response.json()["detail"][0]["msg"]
    )
    create_mock.assert_not_awaited()


def test_list_workout_sets_returns_owner_page(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client
    workout_id = uuid4()
    workout_exercise_id = uuid4()
    workout_sets = [
        make_workout_set(workout_exercise_id, set_number=1),
        make_workout_set(
            workout_exercise_id,
            set_number=2,
            reps=6,
        ),
    ]

    async def fake_list_workout_sets(
        session: object,
        requested_workout_id: UUID,
        requested_workout_exercise_id: UUID,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[SimpleNamespace], int]:
        assert session is not None
        assert requested_workout_id == workout_id
        assert requested_workout_exercise_id == workout_exercise_id
        assert user_id == current_user.id
        assert limit == 10
        assert offset == 5

        return workout_sets, 2

    monkeypatch.setattr(
        workout_set_routes,
        "list_owned_workout_sets_service",
        fake_list_workout_sets,
    )

    response = client.get(
        (f"/workouts/{workout_id}/exercises/{workout_exercise_id}/sets"),
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
    assert [workout_set["set_number"] for workout_set in response_data["items"]] == [
        1,
        2,
    ]


def test_list_workout_sets_hides_missing_or_unowned_parent(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = authenticated_client

    async def fake_list_workout_sets(
        _session: object,
        _workout_id: UUID,
        _workout_exercise_id: UUID,
        _user_id: UUID,
        _limit: int,
        _offset: int,
    ) -> None:
        return None

    monkeypatch.setattr(
        workout_set_routes,
        "list_owned_workout_sets_service",
        fake_list_workout_sets,
    )

    response = client.get(f"/workouts/{uuid4()}/exercises/{uuid4()}/sets")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Workout exercise not found.",
    }


def test_get_workout_set_returns_owned_set(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client
    workout_id = uuid4()
    workout_exercise_id = uuid4()
    workout_set = make_workout_set(workout_exercise_id)

    async def fake_get_owned_workout_set(
        session: object,
        requested_workout_id: UUID,
        requested_workout_exercise_id: UUID,
        workout_set_id: UUID,
        user_id: UUID,
    ) -> SimpleNamespace:
        assert session is not None
        assert requested_workout_id == workout_id
        assert requested_workout_exercise_id == workout_exercise_id
        assert workout_set_id == workout_set.id
        assert user_id == current_user.id

        return workout_set

    monkeypatch.setattr(
        workout_set_routes,
        "get_owned_workout_set_service",
        fake_get_owned_workout_set,
    )

    response = client.get(
        f"/workouts/{workout_id}/exercises/{workout_exercise_id}/sets/{workout_set.id}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(workout_set.id)


@pytest.mark.parametrize(
    ("method", "request_body"),
    [
        ("GET", None),
        ("PATCH", {"notes": "Changed"}),
        ("DELETE", None),
    ],
)
def test_workout_set_endpoints_hide_missing_or_unowned_set(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    request_body: dict[str, object] | None,
) -> None:
    client, _ = authenticated_client
    url = f"/workouts/{uuid4()}/exercises/{uuid4()}/sets/{uuid4()}"

    async def fake_get_owned_workout_set(
        _session: object,
        _workout_id: UUID,
        _workout_exercise_id: UUID,
        _workout_set_id: UUID,
        _user_id: UUID,
    ) -> None:
        return None

    monkeypatch.setattr(
        workout_set_routes,
        "get_owned_workout_set_service",
        fake_get_owned_workout_set,
    )

    if request_body is None:
        response = client.request(method, url)
    else:
        response = client.request(
            method,
            url,
            json=request_body,
        )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Workout set not found.",
    }


def test_update_workout_set_applies_patch(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = authenticated_client
    workout_id = uuid4()
    workout_exercise_id = uuid4()
    workout_set = make_workout_set(workout_exercise_id)

    async def fake_get_owned_workout_set(
        _session: object,
        _workout_id: UUID,
        _workout_exercise_id: UUID,
        _workout_set_id: UUID,
        _user_id: UUID,
    ) -> SimpleNamespace:
        return workout_set

    async def fake_update_workout_set(
        session: object,
        database_workout_set: SimpleNamespace,
        workout_set_data: WorkoutSetUpdate,
    ) -> SimpleNamespace:
        assert session is not None
        assert database_workout_set is workout_set
        assert workout_set_data.set_number == 2
        assert workout_set_data.reps == 10
        assert workout_set_data.weight_kg is None
        assert workout_set_data.rpe == Decimal("9.0")
        assert workout_set_data.notes == "Final working set"

        workout_set.set_number = workout_set_data.set_number
        workout_set.reps = workout_set_data.reps
        workout_set.weight_kg = workout_set_data.weight_kg
        workout_set.rpe = workout_set_data.rpe
        workout_set.notes = workout_set_data.notes
        workout_set.updated_at = datetime.now(UTC)

        return workout_set

    monkeypatch.setattr(
        workout_set_routes,
        "get_owned_workout_set_service",
        fake_get_owned_workout_set,
    )
    monkeypatch.setattr(
        workout_set_routes,
        "update_workout_set_service",
        fake_update_workout_set,
    )

    response = client.patch(
        (
            f"/workouts/{workout_id}/exercises/"
            f"{workout_exercise_id}/sets/{workout_set.id}"
        ),
        json={
            "set_number": 2,
            "reps": 10,
            "weight_kg": None,
            "rpe": "9.0",
            "notes": "  Final working set  ",
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["set_number"] == 2
    assert response_data["reps"] == 10
    assert response_data["weight_kg"] is None
    assert response_data["rpe"] == "9.0"
    assert response_data["notes"] == "Final working set"


def test_update_workout_set_maps_set_number_conflict(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = authenticated_client
    workout_id = uuid4()
    workout_exercise_id = uuid4()
    workout_set = make_workout_set(workout_exercise_id)

    async def fake_get_owned_workout_set(
        _session: object,
        _workout_id: UUID,
        _workout_exercise_id: UUID,
        _workout_set_id: UUID,
        _user_id: UUID,
    ) -> SimpleNamespace:
        return workout_set

    async def fake_update_workout_set(
        _session: object,
        _workout_set: SimpleNamespace,
        _workout_set_data: WorkoutSetUpdate,
    ) -> None:
        raise WorkoutSetNumberConflictError

    monkeypatch.setattr(
        workout_set_routes,
        "get_owned_workout_set_service",
        fake_get_owned_workout_set,
    )
    monkeypatch.setattr(
        workout_set_routes,
        "update_workout_set_service",
        fake_update_workout_set,
    )

    response = client.patch(
        (
            f"/workouts/{workout_id}/exercises/"
            f"{workout_exercise_id}/sets/{workout_set.id}"
        ),
        json={"set_number": 2},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": ("Set number is already used for this workout exercise."),
    }


def test_update_workout_set_maps_missing_metric_to_422(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = authenticated_client
    workout_id = uuid4()
    workout_exercise_id = uuid4()
    workout_set = make_workout_set(workout_exercise_id)

    async def fake_get_owned_workout_set(
        _session: object,
        _workout_id: UUID,
        _workout_exercise_id: UUID,
        _workout_set_id: UUID,
        _user_id: UUID,
    ) -> SimpleNamespace:
        return workout_set

    async def fake_update_workout_set(
        _session: object,
        _workout_set: SimpleNamespace,
        _workout_set_data: WorkoutSetUpdate,
    ) -> None:
        raise WorkoutSetPerformanceMetricRequiredError

    monkeypatch.setattr(
        workout_set_routes,
        "get_owned_workout_set_service",
        fake_get_owned_workout_set,
    )
    monkeypatch.setattr(
        workout_set_routes,
        "update_workout_set_service",
        fake_update_workout_set,
    )

    response = client.patch(
        (
            f"/workouts/{workout_id}/exercises/"
            f"{workout_exercise_id}/sets/{workout_set.id}"
        ),
        json={"reps": None},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "At least one performance metric must be provided.",
    }


def test_delete_workout_set_returns_no_content(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = authenticated_client
    workout_id = uuid4()
    workout_exercise_id = uuid4()
    workout_set = make_workout_set(workout_exercise_id)

    async def fake_get_owned_workout_set(
        _session: object,
        _workout_id: UUID,
        _workout_exercise_id: UUID,
        _workout_set_id: UUID,
        _user_id: UUID,
    ) -> SimpleNamespace:
        return workout_set

    delete_mock = AsyncMock()

    monkeypatch.setattr(
        workout_set_routes,
        "get_owned_workout_set_service",
        fake_get_owned_workout_set,
    )
    monkeypatch.setattr(
        workout_set_routes,
        "delete_workout_set_service",
        delete_mock,
    )

    response = client.delete(
        f"/workouts/{workout_id}/exercises/{workout_exercise_id}/sets/{workout_set.id}"
    )

    assert response.status_code == 204
    assert response.content == b""
    delete_mock.assert_awaited_once_with(
        ANY,
        workout_set,
    )


@pytest.mark.parametrize(
    ("method", "path_suffix", "request_body"),
    [
        ("POST", "", {"reps": 8}),
        ("GET", "", None),
        ("GET", f"/{uuid4()}", None),
        ("PATCH", f"/{uuid4()}", {"reps": 10}),
        ("DELETE", f"/{uuid4()}", None),
    ],
)
def test_workout_set_endpoints_require_authentication(
    method: str,
    path_suffix: str,
    request_body: dict[str, object] | None,
) -> None:
    collection_url = f"/workouts/{uuid4()}/exercises/{uuid4()}/sets"

    with TestClient(app) as client:
        if request_body is None:
            response = client.request(
                method,
                f"{collection_url}{path_suffix}",
            )
        else:
            response = client.request(
                method,
                f"{collection_url}{path_suffix}",
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
def test_list_workout_sets_rejects_invalid_pagination(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
    query_parameters: dict[str, int],
    invalid_field: str,
) -> None:
    client, _ = authenticated_client
    list_mock = AsyncMock()

    monkeypatch.setattr(
        workout_set_routes,
        "list_owned_workout_sets_service",
        list_mock,
    )

    response = client.get(
        (f"/workouts/{uuid4()}/exercises/{uuid4()}/sets"),
        params=query_parameters,
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == invalid_field
    list_mock.assert_not_awaited()


def test_workout_set_openapi_documents_security_and_responses() -> None:
    schema = app.openapi()
    collection_operations = schema["paths"][
        ("/workouts/{workout_id}/exercises/{workout_exercise_id}/sets")
    ]
    item_operations = schema["paths"][
        ("/workouts/{workout_id}/exercises/{workout_exercise_id}/sets/{workout_set_id}")
    ]
    operations = [
        collection_operations["get"],
        collection_operations["post"],
        item_operations["get"],
        item_operations["patch"],
        item_operations["delete"],
    ]

    for operation in operations:
        assert operation["security"] == [
            {"OAuth2PasswordBearer": []},
        ]
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

    response_properties = schema["components"]["schemas"]["WorkoutSetResponse"][
        "properties"
    ]

    assert "workout_exercise_id" not in response_properties
