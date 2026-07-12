from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings

ACCESS_TOKEN_TYPE = "access"
REQUIRED_ACCESS_TOKEN_CLAIMS = ("sub", "type", "iat", "exp", "iss", "aud")

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(
    subject: UUID | str,
    expires_delta: timedelta | None = None,
) -> str:
    issued_at = datetime.now(UTC)

    if expires_delta is None:
        expires_delta = timedelta(
            minutes=settings.jwt_access_token_expire_minutes,
        )

    payload = {
        "sub": str(subject),
        "type": ACCESS_TOKEN_TYPE,
        "iat": issued_at,
        "exp": issued_at + expires_delta,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, object]:
    payload = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": list(REQUIRED_ACCESS_TOKEN_CLAIMS)},
    )

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise InvalidTokenError("Invalid token type.")

    return payload
