from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate, UserResponse

TEST_PASSWORD = "correct-horse-battery-staple"


def test_user_create_normalizes_email_and_hides_password() -> None:
    user_data = UserCreate(
        email="  Roman.User@Example.COM  ",
        password=TEST_PASSWORD,
    )

    assert str(user_data.email) == "roman.user@example.com"
    assert user_data.password.get_secret_value() == TEST_PASSWORD
    assert TEST_PASSWORD not in repr(user_data)


def test_user_create_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        UserCreate(
            email="not-an-email",
            password=TEST_PASSWORD,
        )


def test_user_create_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        UserCreate(
            email="roman@example.com",
            password="short",
        )


def test_user_response_excludes_password_hash() -> None:
    user_id = uuid4()
    now = datetime.now(UTC)

    database_user = SimpleNamespace(
        id=user_id,
        email="roman@example.com",
        hashed_password="$argon2id$sensitive-hash",
        created_at=now,
        updated_at=now,
    )

    response = UserResponse.model_validate(database_user)
    response_data = response.model_dump()

    assert response_data["id"] == user_id
    assert "password" not in response_data
    assert "hashed_password" not in response_data
