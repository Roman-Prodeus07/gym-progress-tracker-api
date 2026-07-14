from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import User, WorkoutSession
from app.schemas import (
    ErrorResponse,
    WorkoutSessionCreate,
    WorkoutSessionListResponse,
    WorkoutSessionResponse,
    WorkoutSessionUpdate,
)
from app.services import InvalidWorkoutTimeRangeError
from app.services import create_workout_session as create_workout_session_service
from app.services import delete_workout_session as delete_workout_session_service
from app.services import (
    get_owned_workout_session as get_owned_workout_session_service,
)
from app.services import list_workout_sessions as list_workout_sessions_service
from app.services import update_workout_session as update_workout_session_service

WORKOUT_NOT_FOUND_DETAIL = "Workout not found."
INVALID_TIME_RANGE_DETAIL = "completed_at cannot be earlier than started_at."

router = APIRouter(
    prefix="/workouts",
    tags=["Workouts"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication required.",
        },
    },
)


async def _get_owned_workout_or_404(
    session: AsyncSession,
    workout_id: UUID,
    user_id: UUID,
) -> WorkoutSession:
    workout = await get_owned_workout_session_service(
        session,
        workout_id,
        user_id,
    )

    if workout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND_DETAIL,
        )

    return workout


@router.post(
    "",
    response_model=WorkoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workout session",
)
async def create_workout(
    workout_data: WorkoutSessionCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkoutSessionResponse:
    workout = await create_workout_session_service(
        session,
        current_user.id,
        workout_data,
    )

    return WorkoutSessionResponse.model_validate(workout)


@router.get(
    "",
    response_model=WorkoutSessionListResponse,
    summary="List workout sessions",
)
async def list_workouts(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WorkoutSessionListResponse:
    workouts, total = await list_workout_sessions_service(
        session,
        current_user.id,
        limit,
        offset,
    )

    return WorkoutSessionListResponse(
        items=[WorkoutSessionResponse.model_validate(workout) for workout in workouts],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{workout_id}",
    response_model=WorkoutSessionResponse,
    summary="Get a workout session",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": WORKOUT_NOT_FOUND_DETAIL,
        },
    },
)
async def get_workout(
    workout_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkoutSessionResponse:
    workout = await _get_owned_workout_or_404(
        session,
        workout_id,
        current_user.id,
    )

    return WorkoutSessionResponse.model_validate(workout)


@router.patch(
    "/{workout_id}",
    response_model=WorkoutSessionResponse,
    summary="Update a workout session",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": WORKOUT_NOT_FOUND_DETAIL,
        },
    },
)
async def update_workout(
    workout_id: UUID,
    workout_data: WorkoutSessionUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkoutSessionResponse:
    workout = await _get_owned_workout_or_404(
        session,
        workout_id,
        current_user.id,
    )

    try:
        updated_workout = await update_workout_session_service(
            session,
            workout,
            workout_data,
        )
    except InvalidWorkoutTimeRangeError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=INVALID_TIME_RANGE_DETAIL,
        ) from error

    return WorkoutSessionResponse.model_validate(updated_workout)


@router.delete(
    "/{workout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workout session",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": WORKOUT_NOT_FOUND_DETAIL,
        },
    },
)
async def delete_workout(
    workout_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    workout = await _get_owned_workout_or_404(
        session,
        workout_id,
        current_user.id,
    )

    await delete_workout_session_service(session, workout)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
