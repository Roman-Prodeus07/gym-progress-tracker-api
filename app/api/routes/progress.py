from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas import (
    ErrorResponse,
    PersonalRecordListResponse,
    ProgressSummaryQuery,
    ProgressSummaryResponse,
)
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
