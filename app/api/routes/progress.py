from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas import ErrorResponse, PersonalRecordListResponse
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
