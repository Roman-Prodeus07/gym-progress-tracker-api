from datetime import timedelta
from uuid import uuid4

import jwt
import pytest
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidSignatureError,
    InvalidTokenError,
    MissingRequiredClaimError,
)

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token


def decode_without_verification(token: str) -> dict[str, object]:
    return jwt.decode(
        token,
        options={"verify_signature": False},
    )


def sign_payload(payload: dict[str, object], secret: str) -> str:
    return jwt.encode(
        payload,
        secret,
        algorithm=settings.jwt_algorithm,
    )


def test_access_token_round_trip() -> None:
    user_id = uuid4()

    token = create_access_token(user_id)
    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    assert payload["iss"] == settings.jwt_issuer
    assert payload["aud"] == settings.jwt_audience
    assert payload["exp"] - payload["iat"] == (
        settings.jwt_access_token_expire_minutes * 60
    )


def test_expired_access_token_is_rejected() -> None:
    token = create_access_token(
        uuid4(),
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(ExpiredSignatureError):
        decode_access_token(token)


def test_access_token_with_invalid_signature_is_rejected() -> None:
    token = create_access_token(uuid4())
    payload = decode_without_verification(token)
    forged_token = sign_payload(payload, "x" * 64)

    with pytest.raises(InvalidSignatureError):
        decode_access_token(forged_token)


def test_non_access_token_is_rejected() -> None:
    token = create_access_token(uuid4())
    payload = decode_without_verification(token)
    payload["type"] = "refresh"

    token_with_wrong_type = sign_payload(
        payload,
        settings.jwt_secret_key.get_secret_value(),
    )

    with pytest.raises(InvalidTokenError, match="Invalid token type"):
        decode_access_token(token_with_wrong_type)


def test_access_token_without_subject_is_rejected() -> None:
    token = create_access_token(uuid4())
    payload = decode_without_verification(token)
    payload.pop("sub")

    token_without_subject = sign_payload(
        payload,
        settings.jwt_secret_key.get_secret_value(),
    )

    with pytest.raises(MissingRequiredClaimError):
        decode_access_token(token_without_subject)
