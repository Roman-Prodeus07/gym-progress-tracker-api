from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas import ErrorResponse, ExerciseListResponse, ExerciseResponse
from app.services import get_active_exercise as get_active_exercise_service
from app.services import list_active_exercises as list_active_exercises_service

EXERCISE_NOT_FOUND_DETAIL = "Exercise not found."

router = APIRouter(
    prefix="/exercises",
    tags=["Exercises"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication required.",
        },
    },
)


@router.get(
    "",
    response_model=ExerciseListResponse,
    summary="List catalogue exercises",
)
async def list_exercises(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ExerciseListResponse:
    exercises, total = await list_active_exercises_service(
        session,
        limit,
        offset,
    )

    return ExerciseListResponse(
        items=[ExerciseResponse.model_validate(exercise) for exercise in exercises],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{exercise_id}",
    response_model=ExerciseResponse,
    summary="Get a catalogue exercise",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": EXERCISE_NOT_FOUND_DETAIL,
        },
    },
)
async def get_exercise(
    exercise_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ExerciseResponse:
    exercise = await get_active_exercise_service(
        session,
        exercise_id,
    )

    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EXERCISE_NOT_FOUND_DETAIL,
        )

    return ExerciseResponse.model_validate(exercise)
