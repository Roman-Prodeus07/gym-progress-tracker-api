from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class TokenPayload(BaseModel):
    sub: UUID
    type: Literal["access"]
    iat: AwareDatetime
    exp: AwareDatetime
    iss: str
    aud: str
