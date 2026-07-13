from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.main import app


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


def test_users_me_returns_safe_current_user_response(
    client: TestClient,
) -> None:
    user_id = uuid4()
    now = datetime.now(UTC)
    user = SimpleNamespace(
        id=user_id,
        email="roman@example.com",
        hashed_password="$argon2id$sensitive-hash",
        created_at=now,
        updated_at=now,
    )

    async def override_get_current_user() -> SimpleNamespace:
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = client.get("/users/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user_id),
        "email": "roman@example.com",
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "updated_at": now.isoformat().replace("+00:00", "Z"),
    }
    assert "hashed_password" not in response.json()


def test_users_me_rejects_missing_token(
    client: TestClient,
) -> None:
    response = client.get("/users/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_users_me_rejects_malformed_token(
    client: TestClient,
) -> None:
    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Could not validate credentials.",
    }
    assert response.headers["www-authenticate"] == "Bearer"


def test_users_me_openapi_uses_oauth2_security() -> None:
    schema = app.openapi()
    operation = schema["paths"]["/users/me"]["get"]
    security_scheme = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]

    assert operation["security"] == [{"OAuth2PasswordBearer": []}]
    assert operation["responses"]["401"]["description"] == (
        "Authentication required or credentials invalid."
    )
    assert security_scheme["type"] == "oauth2"
    assert security_scheme["flows"]["password"]["tokenUrl"] == "auth/login"
