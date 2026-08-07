from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import progress as progress_routes
from app.db.session import get_db_session
from app.main import app
from app.schemas import (
    PersonalRecordResponse,
    PersonalRecordType,
    ProgressAggregateResponse,
    ProgressBucket,
    ProgressBucketResponse,
    ProgressSummaryPeriodResponse,
    ProgressSummaryResponse,
)


@pytest.fixture
def authenticated_client() -> Iterator[tuple[TestClient, SimpleNamespace]]:
    current_user = SimpleNamespace(id=uuid4())

    async def override_get_db_session() -> AsyncGenerator[object]:
        yield object()

    async def override_get_current_user() -> SimpleNamespace:
        return current_user

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        with TestClient(app) as client:
            yield client, current_user
    finally:
        app.dependency_overrides.clear()


def _summary_response() -> ProgressSummaryResponse:
    totals = ProgressAggregateResponse(
        completed_workouts=1,
        active_days=1,
        unique_exercises=1,
        recorded_set_count=4,
        work_set_count=3,
        workout_duration_seconds=3600,
        timed_set_duration_seconds=120,
        total_distance_meters=Decimal("1000.00"),
        total_load_volume=Decimal("1500.000"),
        average_rpe=Decimal("8.5"),
    )

    return ProgressSummaryResponse(
        period=ProgressSummaryPeriodResponse(
            date_from=date(2026, 3, 29),
            date_to=date(2026, 3, 29),
            timezone="Europe/London",
            bucket=ProgressBucket.DAY,
        ),
        totals=totals,
        buckets=[
            ProgressBucketResponse(
                bucket_start=date(2026, 3, 29),
                **totals.model_dump(),
            )
        ],
    )


def test_get_progress_summary_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/progress/summary",
            params={
                "date_from": "2026-03-29",
                "date_to": "2026-03-29",
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_get_progress_summary_returns_owner_summary_and_forwards_timezone(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client
    summary = _summary_response()
    summary_service = AsyncMock(return_value=summary)

    monkeypatch.setattr(
        progress_routes,
        "get_progress_summary_service",
        summary_service,
    )

    response = client.get(
        "/progress/summary",
        params={
            "date_from": "2026-03-29",
            "date_to": "2026-03-29",
            "timezone": "Europe/London",
            "bucket": "day",
        },
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["period"] == {
        "date_from": "2026-03-29",
        "date_to": "2026-03-29",
        "timezone": "Europe/London",
        "bucket": "day",
    }
    assert response_data["totals"]["completed_workouts"] == 1
    assert response_data["totals"]["total_load_volume"] == "1500.000"
    assert response_data["buckets"][0]["bucket_start"] == "2026-03-29"

    service_session, service_user_id, service_query = summary_service.await_args.args
    assert service_session is not None
    assert service_user_id == current_user.id
    assert service_query.date_from == date(2026, 3, 29)
    assert service_query.date_to == date(2026, 3, 29)
    assert service_query.timezone == "Europe/London"
    assert service_query.bucket is ProgressBucket.DAY


def test_get_progress_summary_uses_query_defaults(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = authenticated_client
    summary_service = AsyncMock(return_value=_summary_response())
    monkeypatch.setattr(
        progress_routes,
        "get_progress_summary_service",
        summary_service,
    )

    response = client.get(
        "/progress/summary",
        params={
            "date_from": "2026-03-29",
            "date_to": "2026-03-29",
        },
    )

    assert response.status_code == 200
    service_query = summary_service.await_args.args[2]
    assert service_query.timezone == "UTC"
    assert service_query.bucket is ProgressBucket.WEEK


@pytest.mark.parametrize(
    "params",
    [
        {
            "date_from": "2026-04-02",
            "date_to": "2026-04-01",
        },
        {
            "date_from": "2024-01-01",
            "date_to": "2025-01-01",
        },
        {
            "date_from": "2026-04-01",
            "date_to": "2026-04-02",
            "timezone": "Not/A_Timezone",
        },
        {
            "date_from": "2026-04-01",
            "date_to": "2026-04-02",
            "bucket": "year",
        },
    ],
)
def test_get_progress_summary_rejects_invalid_query(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
    params: dict[str, str],
) -> None:
    client, _ = authenticated_client
    summary_service = AsyncMock()
    monkeypatch.setattr(
        progress_routes,
        "get_progress_summary_service",
        summary_service,
    )

    response = client.get("/progress/summary", params=params)

    assert response.status_code == 422
    summary_service.assert_not_awaited()


def test_list_personal_records_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/progress/personal-records")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_list_personal_records_returns_owner_page(
    authenticated_client: tuple[TestClient, SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, current_user = authenticated_client

    record = PersonalRecordResponse(
        exercise_id=uuid4(),
        exercise_name="Bench Press",
        record_type=PersonalRecordType.MAX_WEIGHT,
        value=Decimal("100.000"),
        workout_id=uuid4(),
        workout_exercise_id=uuid4(),
        workout_set_id=uuid4(),
        achieved_at=datetime(2026, 8, 1, 10, 30, tzinfo=UTC),
        reps=5,
        weight_kg=Decimal("100.000"),
        duration_seconds=None,
        distance_meters=None,
    )

    list_service = AsyncMock(return_value=([record], 1))

    monkeypatch.setattr(
        progress_routes,
        "list_personal_records_service",
        list_service,
    )

    response = client.get(
        "/progress/personal-records",
        params={
            "limit": 25,
            "offset": 5,
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["total"] == 1
    assert response_data["limit"] == 25
    assert response_data["offset"] == 5
    assert len(response_data["items"]) == 1
    assert response_data["items"][0]["exercise_id"] == str(record.exercise_id)
    assert response_data["items"][0]["exercise_name"] == "Bench Press"
    assert response_data["items"][0]["record_type"] == "max_weight"

    list_service.assert_awaited_once_with(
        ANY,
        current_user.id,
        25,
        5,
    )
