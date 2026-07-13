from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.security import create_access_token, decode_access_token
from app.schemas import TokenPayload, TokenResponse


def test_token_response_uses_bearer_type() -> None:
    response = TokenResponse(access_token="encoded.jwt.token")

    assert response.model_dump() == {
        "access_token": "encoded.jwt.token",
        "token_type": "bearer",
    }


def test_token_payload_parses_decoded_access_token() -> None:
    user_id = uuid4()
    token = create_access_token(user_id)
    decoded_payload = decode_access_token(token)

    payload = TokenPayload.model_validate(decoded_payload)

    assert payload.sub == user_id
    assert payload.type == "access"
    assert payload.iat.tzinfo is not None
    assert payload.exp.tzinfo is not None
    assert payload.exp > payload.iat


def test_token_payload_rejects_invalid_subject() -> None:
    token = create_access_token(uuid4())
    decoded_payload = decode_access_token(token)
    decoded_payload["sub"] = "not-a-valid-uuid"

    with pytest.raises(ValidationError):
        TokenPayload.model_validate(decoded_payload)
