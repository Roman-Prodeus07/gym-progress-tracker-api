from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

ZERO: Final = Decimal("0")
THREE_PLACE_QUANTUM: Final = Decimal("0.001")
DISTANCE_QUANTUM: Final = Decimal("0.01")
RPE_QUANTUM: Final = Decimal("0.1")

WORKLOAD_SET_TYPES: Final[frozenset[str]] = frozenset(
    {
        "working",
        "drop",
        "failure",
    }
)
PERSONAL_RECORD_SET_TYPES: Final[frozenset[str]] = frozenset(
    {
        "working",
        "failure",
    }
)


def calculate_load_volume(
    weight_kg: Decimal | None,
    reps: int | None,
) -> Decimal:
    if weight_kg is None or reps is None:
        return ZERO

    return weight_kg * reps


def calculate_estimated_1rm(
    weight_kg: Decimal | None,
    reps: int | None,
) -> Decimal | None:
    if weight_kg is None or weight_kg <= ZERO or reps is None or not 1 <= reps <= 12:
        return None

    if reps == 1:
        return weight_kg

    return weight_kg * (Decimal(1) + Decimal(reps) / Decimal(30))


def calculate_pace_seconds_per_km(
    distance_meters: Decimal | None,
    duration_seconds: int | None,
) -> Decimal | None:
    if (
        distance_meters is None
        or distance_meters <= ZERO
        or duration_seconds is None
        or duration_seconds <= 0
    ):
        return None

    return Decimal(duration_seconds) * Decimal(1000) / distance_meters


def calculate_decimal_average(
    values: Iterable[Decimal],
) -> Decimal | None:
    total = ZERO
    count = 0

    for value in values:
        total += value
        count += 1

    if count == 0:
        return None

    return total / Decimal(count)


def round_decimal(
    value: Decimal,
    quantum: Decimal,
) -> Decimal:
    return value.quantize(
        quantum,
        rounding=ROUND_HALF_UP,
    )
