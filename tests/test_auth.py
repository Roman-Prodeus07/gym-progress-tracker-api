from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes import auth as auth_routes
from app.db.session import get_db_session
from app.main import app
from app.schemas import UserCreate
from app.services import EmailAlreadyRegisteredError


@pytest.fixture
def client() -> Iterator[TestClient]:
    async def override_get_db_session() -> AsyncGenerator[object]:
        yield object()

    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_register_user_returns_safe_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    now = datetime.now(UTC)

    async def fake_register_user(
        session: object,
        user_data: UserCreate,
    ) -> SimpleNamespace:
        assert session is not None
        assert str(user_data.email) == "roman@example.com"

        return SimpleNamespace(
            id=user_id,
            email=str(user_data.email),
            hashed_password="$argon2id$sensitive-hash",
            created_at=now,
            updated_at=now,
        )

    monkeypatch.setattr(
        auth_routes,
        "register_user_service",
        fake_register_user,
    )

    response = client.post(
        "/auth/register",
        json={
            "email": "Roman@Example.COM",
            "password": "StrongPassword-2026!",
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["id"] == str(user_id)
    assert response_data["email"] == "roman@example.com"
    assert set(response_data) == {
        "id",
        "email",
        "created_at",
        "updated_at",
    }


def test_register_user_returns_conflict_for_duplicate_email(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_register_user(
        session: object,
        user_data: UserCreate,
    ) -> None:
        raise EmailAlreadyRegisteredError

    monkeypatch.setattr(
        auth_routes,
        "register_user_service",
        fake_register_user,
    )

    response = client.post(
        "/auth/register",
        json={
            "email": "roman@example.com",
            "password": "StrongPassword-2026!",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "A user with this email already exists."}


@pytest.mark.parametrize(
    ("request_body", "invalid_field"),
    [
        (
            {
                "email": "not-an-email",
                "password": "StrongPassword-2026!",
            },
            "email",
        ),
        (
            {
                "email": "another@example.com",
                "password": "short",
            },
            "password",
        ),
    ],
)
def test_register_user_rejects_invalid_input(
    client: TestClient,
    request_body: dict[str, str],
    invalid_field: str,
) -> None:
    response = client.post(
        "/auth/register",
        json=request_body,
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == invalid_field


def test_register_openapi_documents_conflict_response() -> None:
    responses = app.openapi()["paths"]["/auth/register"]["post"]["responses"]

    assert "201" in responses
    assert "409" in responses
    assert responses["409"]["description"] == ("A user with this email already exists.")
