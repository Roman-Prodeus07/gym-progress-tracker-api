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
from app.models import User, WorkoutSet
from app.schemas import (
    ErrorResponse,
    WorkoutSetCreate,
    WorkoutSetListResponse,
    WorkoutSetResponse,
    WorkoutSetUpdate,
)
from app.services import (
    WorkoutSetNumberConflictError,
    WorkoutSetPerformanceMetricRequiredError,
)
from app.services import create_workout_set as create_workout_set_service
from app.services import delete_workout_set as delete_workout_set_service
from app.services import (
    get_owned_workout_set as get_owned_workout_set_service,
)
from app.services import (
    list_owned_workout_sets as list_owned_workout_sets_service,
)
from app.services import update_workout_set as update_workout_set_service

WORKOUT_EXERCISE_NOT_FOUND_DETAIL = "Workout exercise not found."
WORKOUT_SET_NOT_FOUND_DETAIL = "Workout set not found."
SET_NUMBER_CONFLICT_DETAIL = "Set number is already used for this workout exercise."
PERFORMANCE_METRIC_REQUIRED_DETAIL = "At least one performance metric must be provided."

router = APIRouter(
    prefix=("/workouts/{workout_id}/exercises/{workout_exercise_id}/sets"),
    tags=["Workout Sets"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication required.",
        },
    },
)


def _raise_set_number_conflict(
    error: WorkoutSetNumberConflictError,
) -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=SET_NUMBER_CONFLICT_DETAIL,
    ) from error


async def _get_owned_workout_set_or_404(
    session: AsyncSession,
    workout_id: UUID,
    workout_exercise_id: UUID,
    workout_set_id: UUID,
    user_id: UUID,
) -> WorkoutSet:
    workout_set = await get_owned_workout_set_service(
        session,
        workout_id,
        workout_exercise_id,
        workout_set_id,
        user_id,
    )

    if workout_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_SET_NOT_FOUND_DETAIL,
        )

    return workout_set


@router.post(
    "",
    response_model=WorkoutSetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a set to a workout exercise",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": WORKOUT_EXERCISE_NOT_FOUND_DETAIL,
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": SET_NUMBER_CONFLICT_DETAIL,
        },
    },
)
async def create_workout_set(
    workout_id: UUID,
    workout_exercise_id: UUID,
    workout_set_data: WorkoutSetCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkoutSetResponse:
    try:
        workout_set = await create_workout_set_service(
            session,
            workout_id,
            workout_exercise_id,
            current_user.id,
            workout_set_data,
        )
    except WorkoutSetNumberConflictError as error:
        _raise_set_number_conflict(error)

    if workout_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_EXERCISE_NOT_FOUND_DETAIL,
        )

    return WorkoutSetResponse.model_validate(workout_set)


@router.get(
    "",
    response_model=WorkoutSetListResponse,
    summary="List sets for a workout exercise",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": WORKOUT_EXERCISE_NOT_FOUND_DETAIL,
        },
    },
)
async def list_workout_sets(
    workout_id: UUID,
    workout_exercise_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WorkoutSetListResponse:
    result = await list_owned_workout_sets_service(
        session,
        workout_id,
        workout_exercise_id,
        current_user.id,
        limit,
        offset,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_EXERCISE_NOT_FOUND_DETAIL,
        )

    workout_sets, total = result

    return WorkoutSetListResponse(
        items=[
            WorkoutSetResponse.model_validate(workout_set)
            for workout_set in workout_sets
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{workout_set_id}",
    response_model=WorkoutSetResponse,
    summary="Get a workout set",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": WORKOUT_SET_NOT_FOUND_DETAIL,
        },
    },
)
async def get_workout_set(
    workout_id: UUID,
    workout_exercise_id: UUID,
    workout_set_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkoutSetResponse:
    workout_set = await _get_owned_workout_set_or_404(
        session,
        workout_id,
        workout_exercise_id,
        workout_set_id,
        current_user.id,
    )

    return WorkoutSetResponse.model_validate(workout_set)


@router.patch(
    "/{workout_set_id}",
    response_model=WorkoutSetResponse,
    summary="Update a workout set",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": WORKOUT_SET_NOT_FOUND_DETAIL,
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": SET_NUMBER_CONFLICT_DETAIL,
        },
    },
)
async def update_workout_set(
    workout_id: UUID,
    workout_exercise_id: UUID,
    workout_set_id: UUID,
    workout_set_data: WorkoutSetUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkoutSetResponse:
    workout_set = await _get_owned_workout_set_or_404(
        session,
        workout_id,
        workout_exercise_id,
        workout_set_id,
        current_user.id,
    )

    try:
        updated_workout_set = await update_workout_set_service(
            session,
            workout_set,
            workout_set_data,
        )
    except WorkoutSetNumberConflictError as error:
        _raise_set_number_conflict(error)
    except WorkoutSetPerformanceMetricRequiredError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=PERFORMANCE_METRIC_REQUIRED_DETAIL,
        ) from error

    return WorkoutSetResponse.model_validate(updated_workout_set)


@router.delete(
    "/{workout_set_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workout set",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": WORKOUT_SET_NOT_FOUND_DETAIL,
        },
    },
)
async def delete_workout_set(
    workout_id: UUID,
    workout_exercise_id: UUID,
    workout_set_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    workout_set = await _get_owned_workout_set_or_404(
        session,
        workout_id,
        workout_exercise_id,
        workout_set_id,
        current_user.id,
    )

    await delete_workout_set_service(
        session,
        workout_set,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
