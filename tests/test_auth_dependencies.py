from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.dependencies.auth import get_current_user
from app.core.security import create_access_token
from app.models import User


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_get_current_user_returns_token_owner() -> None:
    user_id = uuid4()
    user = SimpleNamespace(id=user_id)
    session = SimpleNamespace(
        get=AsyncMock(return_value=user),
    )
    token = create_access_token(user_id)

    result = await get_current_user(token, session)

    session.get.assert_awaited_once_with(User, user_id)
    assert result is user


@pytest.mark.anyio
async def test_get_current_user_rejects_malformed_token() -> None:
    session = SimpleNamespace(
        get=AsyncMock(),
    )

    with pytest.raises(HTTPException) as exception_info:
        await get_current_user("not-a-valid-jwt", session)

    assert exception_info.value.status_code == 401
    assert exception_info.value.detail == "Could not validate credentials."
    assert exception_info.value.headers == {"WWW-Authenticate": "Bearer"}
    session.get.assert_not_awaited()


@pytest.mark.anyio
async def test_get_current_user_rejects_expired_token() -> None:
    session = SimpleNamespace(
        get=AsyncMock(),
    )
    token = create_access_token(
        uuid4(),
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(HTTPException) as exception_info:
        await get_current_user(token, session)

    assert exception_info.value.status_code == 401
    assert exception_info.value.headers == {"WWW-Authenticate": "Bearer"}
    session.get.assert_not_awaited()


@pytest.mark.anyio
async def test_get_current_user_rejects_unknown_user() -> None:
    user_id = uuid4()
    session = SimpleNamespace(
        get=AsyncMock(return_value=None),
    )
    token = create_access_token(user_id)

    with pytest.raises(HTTPException) as exception_info:
        await get_current_user(token, session)

    session.get.assert_awaited_once_with(User, user_id)
    assert exception_info.value.status_code == 401
    assert exception_info.value.detail == "Could not validate credentials."
    assert exception_info.value.headers == {"WWW-Authenticate": "Bearer"}
