from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas import ErrorResponse, UserCreate, UserResponse
from app.services import EmailAlreadyRegisteredError
from app.services import register_user as register_user_service

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "A user with this email already exists.",
        },
    },
)
async def register_user(
    user_data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    try:
        user = await register_user_service(session, user_data)
    except EmailAlreadyRegisteredError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        ) from error

    return UserResponse.model_validate(user)
