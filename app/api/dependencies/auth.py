from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.models import User
from app.schemas import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/login",
)


def create_credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    try:
        decoded_payload = decode_access_token(token)
        token_payload = TokenPayload.model_validate(decoded_payload)
    except (InvalidTokenError, ValidationError) as error:
        raise create_credentials_exception() from error

    user = await session.get(User, token_payload.sub)

    if user is None:
        raise create_credentials_exception()

    return user
