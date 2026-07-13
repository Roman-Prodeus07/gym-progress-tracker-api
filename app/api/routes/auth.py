from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_db_session
from app.schemas import ErrorResponse, TokenResponse, UserCreate, UserResponse
from app.services import EmailAlreadyRegisteredError
from app.services import authenticate_user as authenticate_user_service
from app.services import register_user as register_user_service

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

INVALID_CREDENTIALS_DETAIL = "Incorrect email or password."


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


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive an access token",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": INVALID_CREDENTIALS_DETAIL,
        },
    },
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    user = await authenticate_user_service(
        session,
        form_data.username,
        form_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
    )
