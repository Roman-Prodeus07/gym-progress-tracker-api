from collections.abc import Iterable
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol
from uuid import UUID

from app.schemas import PersonalRecordResponse, PersonalRecordType
from app.services.progress_calculations import (
    PERSONAL_RECORD_SET_TYPES,
    ZERO,
)

ONE = Decimal("1")
THIRTY = Decimal("30")
METERS_PER_KILOMETER = Decimal("1000")
THREE_DECIMAL_PLACES = Decimal("0.001")


class PersonalRecordCandidate(Protocol):
    exercise_id: UUID
    exercise_name: str
    workout_id: UUID
    workout_exercise_id: UUID
    workout_set_id: UUID
    started_at: datetime
    completed_at: datetime | None
    position: int
    set_number: int
    set_type: str
    reps: int | None
    weight_kg: Decimal | None
    duration_seconds: int | None
    distance_meters: Decimal | None


def _tie_break_key(
    candidate: PersonalRecordCandidate,
) -> tuple[datetime, int, int, str]:
    return (
        candidate.started_at,
        candidate.position,
        candidate.set_number,
        str(candidate.workout_set_id),
    )


def _calculate_estimated_1rm(
    weight_kg: Decimal,
    reps: int,
) -> Decimal:
    estimated_1rm = weight_kg * (ONE + Decimal(reps) / THIRTY)

    return estimated_1rm.quantize(
        THREE_DECIMAL_PLACES,
        rounding=ROUND_HALF_UP,
    )


def select_personal_records(
    candidates: Iterable[PersonalRecordCandidate],
) -> list[PersonalRecordResponse]:
    best_weight_by_exercise: dict[
        UUID,
        tuple[Decimal, PersonalRecordCandidate],
    ] = {}
    best_reps_by_exercise: dict[
        UUID,
        tuple[int, PersonalRecordCandidate],
    ] = {}
    best_volume_by_exercise: dict[
        UUID,
        tuple[Decimal, PersonalRecordCandidate],
    ] = {}
    best_estimated_1rm_by_exercise: dict[
        UUID,
        tuple[Decimal, PersonalRecordCandidate],
    ] = {}
    best_distance_by_exercise: dict[
        UUID,
        tuple[Decimal, PersonalRecordCandidate],
    ] = {}
    best_duration_by_exercise: dict[
        UUID,
        tuple[int, PersonalRecordCandidate],
    ] = {}
    best_pace_by_exercise: dict[
        UUID,
        tuple[Decimal, PersonalRecordCandidate],
    ] = {}

    for candidate in candidates:
        if candidate.completed_at is None:
            continue

        if candidate.set_type not in PERSONAL_RECORD_SET_TYPES:
            continue

        reps = candidate.reps

        if reps is not None and reps > 0:
            current_reps = best_reps_by_exercise.get(candidate.exercise_id)

            if (
                current_reps is None
                or reps > current_reps[0]
                or (
                    reps == current_reps[0]
                    and _tie_break_key(candidate) < _tie_break_key(current_reps[1])
                )
            ):
                best_reps_by_exercise[candidate.exercise_id] = (
                    reps,
                    candidate,
                )

        duration_seconds = candidate.duration_seconds

        if duration_seconds is not None and duration_seconds > 0:
            current_duration = best_duration_by_exercise.get(candidate.exercise_id)

            if (
                current_duration is None
                or duration_seconds > current_duration[0]
                or (
                    duration_seconds == current_duration[0]
                    and _tie_break_key(candidate) < _tie_break_key(current_duration[1])
                )
            ):
                best_duration_by_exercise[candidate.exercise_id] = (
                    duration_seconds,
                    candidate,
                )

        distance_meters = candidate.distance_meters

        if distance_meters is not None and distance_meters > ZERO:
            current_distance = best_distance_by_exercise.get(candidate.exercise_id)

            if (
                current_distance is None
                or distance_meters > current_distance[0]
                or (
                    distance_meters == current_distance[0]
                    and _tie_break_key(candidate) < _tie_break_key(current_distance[1])
                )
            ):
                best_distance_by_exercise[candidate.exercise_id] = (
                    distance_meters,
                    candidate,
                )

        if (
            duration_seconds is not None
            and duration_seconds > 0
            and distance_meters is not None
            and distance_meters > ZERO
        ):
            pace = (
                Decimal(duration_seconds) * METERS_PER_KILOMETER / distance_meters
            ).quantize(
                THREE_DECIMAL_PLACES,
                rounding=ROUND_HALF_UP,
            )

            current_pace = best_pace_by_exercise.get(candidate.exercise_id)

            if (
                current_pace is None
                or pace < current_pace[0]
                or (
                    pace == current_pace[0]
                    and _tie_break_key(candidate) < _tie_break_key(current_pace[1])
                )
            ):
                best_pace_by_exercise[candidate.exercise_id] = (
                    pace,
                    candidate,
                )

        weight_kg = candidate.weight_kg

        if weight_kg is None or weight_kg <= ZERO or reps is None or reps <= 0:
            continue

        set_volume = weight_kg * Decimal(reps)
        current_volume = best_volume_by_exercise.get(candidate.exercise_id)

        if (
            current_volume is None
            or set_volume > current_volume[0]
            or (
                set_volume == current_volume[0]
                and _tie_break_key(candidate) < _tie_break_key(current_volume[1])
            )
        ):
            best_volume_by_exercise[candidate.exercise_id] = (
                set_volume,
                candidate,
            )

        estimated_1rm = _calculate_estimated_1rm(
            weight_kg,
            reps,
        )
        current_estimated_1rm = best_estimated_1rm_by_exercise.get(
            candidate.exercise_id
        )

        if (
            current_estimated_1rm is None
            or estimated_1rm > current_estimated_1rm[0]
            or (
                estimated_1rm == current_estimated_1rm[0]
                and _tie_break_key(candidate) < _tie_break_key(current_estimated_1rm[1])
            )
        ):
            best_estimated_1rm_by_exercise[candidate.exercise_id] = (
                estimated_1rm,
                candidate,
            )

        current_weight = best_weight_by_exercise.get(candidate.exercise_id)

        if (
            current_weight is None
            or weight_kg > current_weight[0]
            or (
                weight_kg == current_weight[0]
                and _tie_break_key(candidate) < _tie_break_key(current_weight[1])
            )
        ):
            best_weight_by_exercise[candidate.exercise_id] = (
                weight_kg,
                candidate,
            )

    records = [
        PersonalRecordResponse(
            exercise_id=candidate.exercise_id,
            exercise_name=candidate.exercise_name,
            record_type=PersonalRecordType.MAX_WEIGHT,
            value=weight_kg,
            workout_id=candidate.workout_id,
            workout_exercise_id=candidate.workout_exercise_id,
            workout_set_id=candidate.workout_set_id,
            achieved_at=candidate.started_at,
            reps=candidate.reps,
            weight_kg=weight_kg,
            duration_seconds=candidate.duration_seconds,
            distance_meters=candidate.distance_meters,
        )
        for weight_kg, candidate in best_weight_by_exercise.values()
    ]

    records.extend(
        PersonalRecordResponse(
            exercise_id=candidate.exercise_id,
            exercise_name=candidate.exercise_name,
            record_type=PersonalRecordType.MAX_REPS,
            value=Decimal(reps),
            workout_id=candidate.workout_id,
            workout_exercise_id=candidate.workout_exercise_id,
            workout_set_id=candidate.workout_set_id,
            achieved_at=candidate.started_at,
            reps=reps,
            weight_kg=candidate.weight_kg,
            duration_seconds=candidate.duration_seconds,
            distance_meters=candidate.distance_meters,
        )
        for reps, candidate in best_reps_by_exercise.values()
    )

    records.extend(
        PersonalRecordResponse(
            exercise_id=candidate.exercise_id,
            exercise_name=candidate.exercise_name,
            record_type=PersonalRecordType.MAX_SET_VOLUME,
            value=set_volume,
            workout_id=candidate.workout_id,
            workout_exercise_id=candidate.workout_exercise_id,
            workout_set_id=candidate.workout_set_id,
            achieved_at=candidate.started_at,
            reps=candidate.reps,
            weight_kg=candidate.weight_kg,
            duration_seconds=candidate.duration_seconds,
            distance_meters=candidate.distance_meters,
        )
        for set_volume, candidate in best_volume_by_exercise.values()
    )

    records.extend(
        PersonalRecordResponse(
            exercise_id=candidate.exercise_id,
            exercise_name=candidate.exercise_name,
            record_type=PersonalRecordType.ESTIMATED_1RM,
            value=estimated_1rm,
            workout_id=candidate.workout_id,
            workout_exercise_id=candidate.workout_exercise_id,
            workout_set_id=candidate.workout_set_id,
            achieved_at=candidate.started_at,
            reps=candidate.reps,
            weight_kg=candidate.weight_kg,
            duration_seconds=candidate.duration_seconds,
            distance_meters=candidate.distance_meters,
        )
        for estimated_1rm, candidate in best_estimated_1rm_by_exercise.values()
    )

    records.extend(
        PersonalRecordResponse(
            exercise_id=candidate.exercise_id,
            exercise_name=candidate.exercise_name,
            record_type=PersonalRecordType.MAX_DISTANCE,
            value=distance_meters,
            workout_id=candidate.workout_id,
            workout_exercise_id=candidate.workout_exercise_id,
            workout_set_id=candidate.workout_set_id,
            achieved_at=candidate.started_at,
            reps=candidate.reps,
            weight_kg=candidate.weight_kg,
            duration_seconds=candidate.duration_seconds,
            distance_meters=distance_meters,
        )
        for distance_meters, candidate in best_distance_by_exercise.values()
    )

    records.extend(
        PersonalRecordResponse(
            exercise_id=candidate.exercise_id,
            exercise_name=candidate.exercise_name,
            record_type=PersonalRecordType.LONGEST_DURATION,
            value=Decimal(duration_seconds),
            workout_id=candidate.workout_id,
            workout_exercise_id=candidate.workout_exercise_id,
            workout_set_id=candidate.workout_set_id,
            achieved_at=candidate.started_at,
            reps=candidate.reps,
            weight_kg=candidate.weight_kg,
            duration_seconds=duration_seconds,
            distance_meters=candidate.distance_meters,
        )
        for duration_seconds, candidate in best_duration_by_exercise.values()
    )

    records.extend(
        PersonalRecordResponse(
            exercise_id=candidate.exercise_id,
            exercise_name=candidate.exercise_name,
            record_type=PersonalRecordType.BEST_PACE,
            value=pace,
            workout_id=candidate.workout_id,
            workout_exercise_id=candidate.workout_exercise_id,
            workout_set_id=candidate.workout_set_id,
            achieved_at=candidate.started_at,
            reps=candidate.reps,
            weight_kg=candidate.weight_kg,
            duration_seconds=candidate.duration_seconds,
            distance_meters=candidate.distance_meters,
        )
        for pace, candidate in best_pace_by_exercise.values()
    )

    records.sort(
        key=lambda record: (
            record.achieved_at,
            str(record.exercise_id),
        ),
        reverse=True,
    )

    return records
