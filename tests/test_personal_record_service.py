from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.dialects import postgresql

import app.services.personal_record as personal_record_service
from app.schemas import PersonalRecordResponse, PersonalRecordType
from app.services.personal_record import select_personal_records


def _candidate(
    *,
    exercise_id: UUID,
    started_at: datetime,
    set_type: str = "working",
    reps: int | None = 5,
    weight_kg: Decimal | None = Decimal("100.000"),
    distance_meters: Decimal | None = None,
    completed: bool = True,
    duration_seconds: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        exercise_id=exercise_id,
        exercise_name="Bench Press",
        workout_id=uuid4(),
        workout_exercise_id=uuid4(),
        workout_set_id=uuid4(),
        started_at=started_at,
        completed_at=(started_at + timedelta(hours=1) if completed else None),
        position=1,
        set_number=1,
        set_type=set_type,
        reps=reps,
        weight_kg=weight_kg,
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
    )


def test_select_personal_records_uses_only_completed_eligible_sets_for_max_weight() -> (
    None
):
    exercise_id = uuid4()
    base_time = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)

    working_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time,
        weight_kg=Decimal("100.000"),
    )
    failure_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=1),
        set_type="failure",
        reps=3,
        weight_kg=Decimal("110.000"),
    )
    warmup_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=2),
        set_type="warmup",
        reps=1,
        weight_kg=Decimal("200.000"),
    )
    drop_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=3),
        set_type="drop",
        reps=1,
        weight_kg=Decimal("190.000"),
    )
    incomplete_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=4),
        reps=1,
        weight_kg=Decimal("220.000"),
        completed=False,
    )
    zero_rep_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=5),
        reps=0,
        weight_kg=Decimal("250.000"),
    )

    records = select_personal_records(
        [
            working_set,
            failure_set,
            warmup_set,
            drop_set,
            incomplete_set,
            zero_rep_set,
        ]
    )

    max_weight_record = next(
        record
        for record in records
        if record.record_type == PersonalRecordType.MAX_WEIGHT
    )

    assert max_weight_record.value == Decimal("110.000")
    assert max_weight_record.workout_set_id == failure_set.workout_set_id
    assert max_weight_record.achieved_at == failure_set.started_at


def test_select_personal_records_selects_max_reps_without_requiring_weight() -> None:
    exercise_id = uuid4()
    base_time = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)

    working_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time,
        reps=10,
        weight_kg=None,
    )
    failure_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=1),
        set_type="failure",
        reps=12,
        weight_kg=None,
    )
    heavier_lower_rep_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=2),
        reps=8,
        weight_kg=Decimal("200.000"),
    )
    warmup_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=3),
        set_type="warmup",
        reps=30,
        weight_kg=None,
    )
    incomplete_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=4),
        reps=40,
        weight_kg=None,
        completed=False,
    )

    records = select_personal_records(
        [
            working_set,
            failure_set,
            heavier_lower_rep_set,
            warmup_set,
            incomplete_set,
        ]
    )
    records_by_type = {record.record_type: record for record in records}

    assert PersonalRecordType.MAX_REPS in records_by_type

    max_reps_record = records_by_type[PersonalRecordType.MAX_REPS]

    assert max_reps_record.value == Decimal("12")
    assert max_reps_record.workout_set_id == failure_set.workout_set_id
    assert max_reps_record.achieved_at == failure_set.started_at
    assert max_reps_record.reps == 12
    assert max_reps_record.weight_kg is None


def test_select_personal_records_selects_max_set_volume() -> None:
    exercise_id = uuid4()
    base_time = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)

    highest_weight_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time,
        reps=5,
        weight_kg=Decimal("120.000"),
    )
    highest_reps_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=1),
        reps=20,
        weight_kg=Decimal("20.000"),
    )
    highest_volume_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=2),
        reps=12,
        weight_kg=Decimal("90.000"),
    )
    warmup_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=3),
        set_type="warmup",
        reps=20,
        weight_kg=Decimal("100.000"),
    )
    incomplete_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=4),
        reps=20,
        weight_kg=Decimal("110.000"),
        completed=False,
    )

    records = select_personal_records(
        [
            highest_weight_set,
            highest_reps_set,
            highest_volume_set,
            warmup_set,
            incomplete_set,
        ]
    )
    records_by_type = {record.record_type: record for record in records}

    assert PersonalRecordType.MAX_SET_VOLUME in records_by_type

    volume_record = records_by_type[PersonalRecordType.MAX_SET_VOLUME]

    assert volume_record.value == Decimal("1080.000")
    assert volume_record.workout_set_id == highest_volume_set.workout_set_id
    assert volume_record.achieved_at == highest_volume_set.started_at
    assert volume_record.reps == 12
    assert volume_record.weight_kg == Decimal("90.000")


def test_select_personal_records_selects_highest_estimated_1rm() -> None:
    exercise_id = uuid4()
    base_time = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)

    highest_weight_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time,
        reps=2,
        weight_kg=Decimal("120.000"),
    )
    higher_reps_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=1),
        reps=12,
        weight_kg=Decimal("50.000"),
    )
    highest_estimated_1rm_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=2),
        reps=10,
        weight_kg=Decimal("100.000"),
    )
    warmup_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=3),
        set_type="warmup",
        reps=10,
        weight_kg=Decimal("200.000"),
    )
    incomplete_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=4),
        reps=10,
        weight_kg=Decimal("180.000"),
        completed=False,
    )

    records = select_personal_records(
        [
            highest_weight_set,
            higher_reps_set,
            highest_estimated_1rm_set,
            warmup_set,
            incomplete_set,
        ]
    )
    records_by_type = {record.record_type: record for record in records}

    assert PersonalRecordType.ESTIMATED_1RM in records_by_type

    estimated_1rm_record = records_by_type[PersonalRecordType.ESTIMATED_1RM]

    assert estimated_1rm_record.value == Decimal("133.333")
    assert (
        estimated_1rm_record.workout_set_id == highest_estimated_1rm_set.workout_set_id
    )
    assert estimated_1rm_record.achieved_at == highest_estimated_1rm_set.started_at
    assert estimated_1rm_record.reps == 10
    assert estimated_1rm_record.weight_kg == Decimal("100.000")


def test_select_personal_records_selects_max_distance() -> None:
    exercise_id = uuid4()
    base_time = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)

    shorter_distance_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time,
        reps=None,
        weight_kg=None,
        distance_meters=Decimal("1000.000"),
    )
    longest_distance_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=1),
        set_type="failure",
        reps=None,
        weight_kg=None,
        distance_meters=Decimal("5000.000"),
    )
    warmup_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=2),
        set_type="warmup",
        reps=None,
        weight_kg=None,
        distance_meters=Decimal("7000.000"),
    )
    incomplete_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=3),
        reps=None,
        weight_kg=None,
        distance_meters=Decimal("8000.000"),
        completed=False,
    )

    records = select_personal_records(
        [
            shorter_distance_set,
            longest_distance_set,
            warmup_set,
            incomplete_set,
        ]
    )
    records_by_type = {record.record_type: record for record in records}

    assert PersonalRecordType.MAX_DISTANCE in records_by_type

    distance_record = records_by_type[PersonalRecordType.MAX_DISTANCE]

    assert distance_record.value == Decimal("5000.000")
    assert distance_record.workout_set_id == longest_distance_set.workout_set_id
    assert distance_record.achieved_at == longest_distance_set.started_at
    assert distance_record.distance_meters == Decimal("5000.000")


def test_select_personal_records_selects_longest_duration() -> None:
    exercise_id = uuid4()
    base_time = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)

    shorter_duration_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time,
        reps=None,
        weight_kg=None,
        duration_seconds=900,
    )
    longest_duration_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=1),
        set_type="failure",
        reps=None,
        weight_kg=None,
        duration_seconds=3600,
    )
    warmup_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=2),
        set_type="warmup",
        reps=None,
        weight_kg=None,
        duration_seconds=7200,
    )
    incomplete_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=3),
        reps=None,
        weight_kg=None,
        duration_seconds=8000,
        completed=False,
    )

    records = select_personal_records(
        [
            shorter_duration_set,
            longest_duration_set,
            warmup_set,
            incomplete_set,
        ]
    )
    records_by_type = {record.record_type: record for record in records}

    assert PersonalRecordType.LONGEST_DURATION in records_by_type

    duration_record = records_by_type[PersonalRecordType.LONGEST_DURATION]

    assert duration_record.value == Decimal("3600")
    assert duration_record.workout_set_id == longest_duration_set.workout_set_id
    assert duration_record.achieved_at == longest_duration_set.started_at
    assert duration_record.duration_seconds == 3600


def test_select_personal_records_selects_best_pace() -> None:
    exercise_id = uuid4()
    base_time = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)

    slower_pace_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time,
        reps=None,
        weight_kg=None,
        duration_seconds=400,
        distance_meters=Decimal("1000.000"),
    )
    best_pace_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=1),
        set_type="failure",
        reps=None,
        weight_kg=None,
        duration_seconds=1500,
        distance_meters=Decimal("5000.000"),
    )
    warmup_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=2),
        set_type="warmup",
        reps=None,
        weight_kg=None,
        duration_seconds=100,
        distance_meters=Decimal("1000.000"),
    )
    incomplete_set = _candidate(
        exercise_id=exercise_id,
        started_at=base_time + timedelta(days=3),
        reps=None,
        weight_kg=None,
        duration_seconds=50,
        distance_meters=Decimal("1000.000"),
        completed=False,
    )

    records = select_personal_records(
        [
            slower_pace_set,
            best_pace_set,
            warmup_set,
            incomplete_set,
        ]
    )
    records_by_type = {record.record_type: record for record in records}

    assert PersonalRecordType.BEST_PACE in records_by_type

    pace_record = records_by_type[PersonalRecordType.BEST_PACE]

    assert pace_record.value == Decimal("300.000")
    assert pace_record.workout_set_id == best_pace_set.workout_set_id
    assert pace_record.achieved_at == best_pace_set.started_at
    assert pace_record.duration_seconds == 1500
    assert pace_record.distance_meters == Decimal("5000.000")


@pytest.mark.anyio
async def test_list_personal_records_scopes_query_and_paginates_after_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    base_time = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)

    candidates = [
        _candidate(
            exercise_id=uuid4(),
            started_at=base_time + timedelta(days=index),
            reps=5,
            weight_kg=Decimal("100.000"),
        )
        for index in range(3)
    ]

    query_result = SimpleNamespace(
        all=Mock(return_value=candidates),
    )
    session = SimpleNamespace(
        execute=AsyncMock(return_value=query_result),
    )

    selected_records = [
        PersonalRecordResponse(
            exercise_id=candidate.exercise_id,
            exercise_name=candidate.exercise_name,
            record_type=PersonalRecordType.MAX_WEIGHT,
            value=Decimal("100.000"),
            workout_id=candidate.workout_id,
            workout_exercise_id=candidate.workout_exercise_id,
            workout_set_id=candidate.workout_set_id,
            achieved_at=candidate.started_at,
            reps=candidate.reps,
            weight_kg=candidate.weight_kg,
            duration_seconds=candidate.duration_seconds,
            distance_meters=candidate.distance_meters,
        )
        for candidate in reversed(candidates)
    ]

    received_candidates: list[object] = []

    def fake_select_personal_records(
        candidate_rows: Iterable[object],
    ) -> list[PersonalRecordResponse]:
        received_candidates.extend(candidate_rows)
        return selected_records

    monkeypatch.setattr(
        personal_record_service,
        "select_personal_records",
        fake_select_personal_records,
    )

    records, total = await personal_record_service.list_personal_records(
        session,
        user_id,
        limit=1,
        offset=1,
    )

    statement = session.execute.await_args.args[0]
    compiled = statement.compile(
        dialect=postgresql.dialect(),
    )
    compiled_sql = " ".join(str(compiled).split())

    assert "WHERE workout_sessions.user_id =" in compiled_sql
    assert user_id in compiled.params.values()
    assert " LIMIT " not in f" {compiled_sql.upper()} "
    assert " OFFSET " not in f" {compiled_sql.upper()} "

    assert received_candidates == candidates
    assert total == 3
    assert records == [selected_records[1]]
