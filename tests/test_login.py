from collections.abc import AsyncGenerator, Iterator
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes import auth as auth_routes
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.main import app
from app.schemas import TokenPayload


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


def test_login_returns_access_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()

    async def fake_authenticate_user(
        session: object,
        email: str,
        password: str,
    ) -> SimpleNamespace:
        assert session is not None
        assert email == "Roman@Example.COM"
        assert password == "StrongPassword-2026!"

        return SimpleNamespace(id=user_id)

    monkeypatch.setattr(
        auth_routes,
        "authenticate_user_service",
        fake_authenticate_user,
    )

    response = client.post(
        "/auth/login",
        data={
            "username": "Roman@Example.COM",
            "password": "StrongPassword-2026!",
        },
    )

    assert response.status_code == 200

    response_data = response.json()
    payload = TokenPayload.model_validate(
        decode_access_token(response_data["access_token"]),
    )

    assert response_data["token_type"] == "bearer"
    assert set(response_data) == {"access_token", "token_type"}
    assert payload.sub == user_id


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("unknown@example.com", "StrongPassword-2026!"),
        ("roman@example.com", "IncorrectPassword-2026!"),
    ],
)
def test_login_rejects_invalid_credentials(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    email: str,
    password: str,
) -> None:
    async def fake_authenticate_user(
        session: object,
        email: str,
        password: str,
    ) -> None:
        return None

    monkeypatch.setattr(
        auth_routes,
        "authenticate_user_service",
        fake_authenticate_user,
    )

    response = client.post(
        "/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Incorrect email or password.",
    }
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_openapi_documents_form_and_unauthorized_response() -> None:
    operation = app.openapi()["paths"]["/auth/login"]["post"]

    assert "application/x-www-form-urlencoded" in operation["requestBody"]["content"]
    assert "200" in operation["responses"]
    assert "401" in operation["responses"]
