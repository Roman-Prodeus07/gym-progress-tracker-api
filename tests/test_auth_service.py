from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.security import hash_password
from app.services import auth as auth_service
from app.services.auth import authenticate_user

TEST_EMAIL = "roman@example.com"
TEST_PASSWORD = "StrongPassword-2026!"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_authenticate_user_accepts_valid_credentials() -> None:
    user = SimpleNamespace(
        email=TEST_EMAIL,
        hashed_password=hash_password(TEST_PASSWORD),
    )
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=user),
    )

    result = await authenticate_user(
        session,
        "  Roman@Example.COM  ",
        TEST_PASSWORD,
    )

    statement = session.scalar.await_args.args[0]

    assert TEST_EMAIL in statement.compile().params.values()
    assert result is user


@pytest.mark.anyio
async def test_authenticate_user_rejects_incorrect_password() -> None:
    user = SimpleNamespace(
        email=TEST_EMAIL,
        hashed_password=hash_password(TEST_PASSWORD),
    )
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=user),
    )

    result = await authenticate_user(
        session,
        TEST_EMAIL,
        "IncorrectPassword-2026!",
    )

    assert result is None


@pytest.mark.anyio
async def test_authenticate_user_rejects_unknown_email_with_dummy_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=None),
    )
    verify_password_mock = Mock(return_value=False)

    monkeypatch.setattr(
        auth_service,
        "verify_password",
        verify_password_mock,
    )

    result = await authenticate_user(
        session,
        "unknown@example.com",
        TEST_PASSWORD,
    )

    assert result is None
    verify_password_mock.assert_called_once_with(
        TEST_PASSWORD,
        auth_service.DUMMY_PASSWORD_HASH,
    )
