from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas import (
    ErrorResponse,
    ExerciseProgressResponse,
    PersonalRecordListResponse,
    ProgressDateRangeParams,
    ProgressSummaryQuery,
    ProgressSummaryResponse,
)
from app.services import get_exercise_progress as get_exercise_progress_service
from app.services import get_progress_summary as get_progress_summary_service
from app.services import list_personal_records as list_personal_records_service

router = APIRouter(
    prefix="/progress",
    tags=["Progress"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication required.",
        },
    },
)

EXERCISE_NOT_FOUND_DETAIL = "Exercise not found."


@router.get(
    "/summary",
    response_model=ProgressSummaryResponse,
    summary="Get progress summary",
)
async def get_progress_summary(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    query: Annotated[ProgressSummaryQuery, Query()],
) -> ProgressSummaryResponse:
    return await get_progress_summary_service(
        session,
        current_user.id,
        query,
    )


@router.get(
    "/exercises/{exercise_id}",
    response_model=ExerciseProgressResponse,
    summary="Get exercise progress",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": EXERCISE_NOT_FOUND_DETAIL,
        },
    },
)
async def get_exercise_progress(
    exercise_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    query: Annotated[ProgressDateRangeParams, Query()],
) -> ExerciseProgressResponse:
    progress = await get_exercise_progress_service(
        session,
        current_user.id,
        exercise_id,
        query,
    )

    if progress is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EXERCISE_NOT_FOUND_DETAIL,
        )

    return progress


@router.get(
    "/personal-records",
    response_model=PersonalRecordListResponse,
    summary="List personal records",
)
async def list_personal_records(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PersonalRecordListResponse:
    records, total = await list_personal_records_service(
        session,
        current_user.id,
        limit,
        offset,
    )

    return PersonalRecordListResponse(
        items=records,
        total=total,
        limit=limit,
        offset=offset,
    )
