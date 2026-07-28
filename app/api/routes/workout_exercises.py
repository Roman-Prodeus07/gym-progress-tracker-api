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
from app.models import User, WorkoutExercise
from app.schemas import (
    ErrorResponse,
    WorkoutExerciseCreate,
    WorkoutExerciseListResponse,
    WorkoutExerciseResponse,
    WorkoutExerciseUpdate,
)
from app.services import (
    ActiveExerciseNotFoundError,
    WorkoutExercisePositionConflictError,
)
from app.services import (
    create_workout_exercise as create_workout_exercise_service,
)
from app.services import (
    delete_workout_exercise as delete_workout_exercise_service,
)
from app.services import (
    get_owned_workout_exercise as get_owned_workout_exercise_service,
)
from app.services import (
    list_owned_workout_exercises as list_owned_workout_exercises_service,
)
from app.services import (
    update_workout_exercise as update_workout_exercise_service,
)

WORKOUT_NOT_FOUND_DETAIL = "Workout not found."
WORKOUT_EXERCISE_NOT_FOUND_DETAIL = "Workout exercise not found."
EXERCISE_NOT_FOUND_DETAIL = "Exercise not found."
POSITION_CONFLICT_DETAIL = "Position is already used in this workout."

router = APIRouter(
    prefix="/workouts/{workout_id}/exercises",
    tags=["Workout Exercises"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication required.",
        },
    },
)


def _raise_position_conflict(
    error: WorkoutExercisePositionConflictError,
) -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=POSITION_CONFLICT_DETAIL,
    ) from error


async def _get_owned_workout_exercise_or_404(
    session: AsyncSession,
    workout_id: UUID,
    workout_exercise_id: UUID,
    user_id: UUID,
) -> WorkoutExercise:
    workout_exercise = await get_owned_workout_exercise_service(
        session,
        workout_id,
        workout_exercise_id,
        user_id,
    )

    if workout_exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_EXERCISE_NOT_FOUND_DETAIL,
        )

    return workout_exercise


@router.post(
    "",
    response_model=WorkoutExerciseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an exercise to a workout",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Workout or active exercise not found.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": POSITION_CONFLICT_DETAIL,
        },
    },
)
async def create_workout_exercise(
    workout_id: UUID,
    workout_exercise_data: WorkoutExerciseCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkoutExerciseResponse:
    try:
        workout_exercise = await create_workout_exercise_service(
            session,
            workout_id,
            current_user.id,
            workout_exercise_data,
        )
    except ActiveExerciseNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EXERCISE_NOT_FOUND_DETAIL,
        ) from error
    except WorkoutExercisePositionConflictError as error:
        _raise_position_conflict(error)

    if workout_exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND_DETAIL,
        )

    return WorkoutExerciseResponse.model_validate(workout_exercise)


@router.get(
    "",
    response_model=WorkoutExerciseListResponse,
    summary="List exercises in a workout",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": WORKOUT_NOT_FOUND_DETAIL,
        },
    },
)
async def list_workout_exercises(
    workout_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WorkoutExerciseListResponse:
    result = await list_owned_workout_exercises_service(
        session,
        workout_id,
        current_user.id,
        limit,
        offset,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND_DETAIL,
        )

    workout_exercises, total = result

    return WorkoutExerciseListResponse(
        items=[
            WorkoutExerciseResponse.model_validate(workout_exercise)
            for workout_exercise in workout_exercises
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{workout_exercise_id}",
    response_model=WorkoutExerciseResponse,
    summary="Get an exercise from a workout",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": WORKOUT_EXERCISE_NOT_FOUND_DETAIL,
        },
    },
)
async def get_workout_exercise(
    workout_id: UUID,
    workout_exercise_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkoutExerciseResponse:
    workout_exercise = await _get_owned_workout_exercise_or_404(
        session,
        workout_id,
        workout_exercise_id,
        current_user.id,
    )

    return WorkoutExerciseResponse.model_validate(workout_exercise)


@router.patch(
    "/{workout_exercise_id}",
    response_model=WorkoutExerciseResponse,
    summary="Update an exercise in a workout",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Workout exercise or active exercise not found.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": POSITION_CONFLICT_DETAIL,
        },
    },
)
async def update_workout_exercise(
    workout_id: UUID,
    workout_exercise_id: UUID,
    workout_exercise_data: WorkoutExerciseUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkoutExerciseResponse:
    workout_exercise = await _get_owned_workout_exercise_or_404(
        session,
        workout_id,
        workout_exercise_id,
        current_user.id,
    )

    try:
        updated_workout_exercise = await update_workout_exercise_service(
            session,
            workout_exercise,
            workout_exercise_data,
        )
    except ActiveExerciseNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EXERCISE_NOT_FOUND_DETAIL,
        ) from error
    except WorkoutExercisePositionConflictError as error:
        _raise_position_conflict(error)

    return WorkoutExerciseResponse.model_validate(updated_workout_exercise)


@router.delete(
    "/{workout_exercise_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an exercise from a workout",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": WORKOUT_EXERCISE_NOT_FOUND_DETAIL,
        },
    },
)
async def delete_workout_exercise(
    workout_id: UUID,
    workout_exercise_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    workout_exercise = await _get_owned_workout_exercise_or_404(
        session,
        workout_id,
        workout_exercise_id,
        current_user.id,
    )

    await delete_workout_exercise_service(
        session,
        workout_exercise,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
