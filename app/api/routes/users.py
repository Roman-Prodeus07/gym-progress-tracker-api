from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user
from app.models import User
from app.schemas import ErrorResponse, UserResponse

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current authenticated user",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication required or credentials invalid.",
        },
    },
)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse.model_validate(current_user)
