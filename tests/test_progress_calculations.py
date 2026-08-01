from decimal import Decimal

import pytest

from app.schemas.progress import PersonalRecordType, ProgressBucket
from app.services.progress_calculations import (
    DISTANCE_QUANTUM,
    PERSONAL_RECORD_SET_TYPES,
    RPE_QUANTUM,
    THREE_PLACE_QUANTUM,
    WORKLOAD_SET_TYPES,
    calculate_decimal_average,
    calculate_estimated_1rm,
    calculate_load_volume,
    calculate_pace_seconds_per_km,
    round_decimal,
)


def test_progress_enums_match_api_contract() -> None:
    assert [bucket.value for bucket in ProgressBucket] == [
        "day",
        "week",
        "month",
    ]
    assert [record_type.value for record_type in PersonalRecordType] == [
        "max_weight",
        "max_reps",
        "max_set_volume",
        "estimated_1rm",
        "max_distance",
        "longest_duration",
        "best_pace",
    ]


def test_set_type_eligibility_matches_domain_contract() -> None:
    assert WORKLOAD_SET_TYPES == frozenset(
        {
            "working",
            "drop",
            "failure",
        }
    )
    assert PERSONAL_RECORD_SET_TYPES == frozenset(
        {
            "working",
            "failure",
        }
    )


def test_calculate_load_volume_preserves_decimal_precision() -> None:
    result = calculate_load_volume(
        weight_kg=Decimal("80.125"),
        reps=8,
    )

    assert result == Decimal("641.000")


@pytest.mark.parametrize(
    ("weight_kg", "reps"),
    [
        (None, 8),
        (Decimal("80.000"), None),
        (Decimal("80.000"), 0),
    ],
)
def test_calculate_load_volume_returns_zero_without_load(
    weight_kg: Decimal | None,
    reps: int | None,
) -> None:
    assert calculate_load_volume(weight_kg, reps) == Decimal("0")


def test_calculate_estimated_1rm_returns_weight_for_single_rep() -> None:
    result = calculate_estimated_1rm(
        weight_kg=Decimal("100.000"),
        reps=1,
    )

    assert result == Decimal("100.000")


def test_calculate_estimated_1rm_uses_epley_formula() -> None:
    result = calculate_estimated_1rm(
        weight_kg=Decimal("90.000"),
        reps=10,
    )

    assert result == Decimal("120.000")


def test_estimated_1rm_is_ranked_before_rounding() -> None:
    result = calculate_estimated_1rm(
        weight_kg=Decimal("80.000"),
        reps=8,
    )

    assert result is not None
    assert result > Decimal("101.333")
    assert round_decimal(
        result,
        THREE_PLACE_QUANTUM,
    ) == Decimal("101.333")


@pytest.mark.parametrize(
    ("weight_kg", "reps"),
    [
        (None, 8),
        (Decimal("0"), 8),
        (Decimal("80.000"), None),
        (Decimal("80.000"), 0),
        (Decimal("80.000"), 13),
    ],
)
def test_calculate_estimated_1rm_rejects_ineligible_sets(
    weight_kg: Decimal | None,
    reps: int | None,
) -> None:
    assert calculate_estimated_1rm(weight_kg, reps) is None


def test_calculate_pace_seconds_per_km() -> None:
    result = calculate_pace_seconds_per_km(
        distance_meters=Decimal("1500.00"),
        duration_seconds=360,
    )

    assert result == Decimal("240")


@pytest.mark.parametrize(
    ("distance_meters", "duration_seconds"),
    [
        (None, 300),
        (Decimal("0"), 300),
        (Decimal("1000.00"), None),
        (Decimal("1000.00"), 0),
    ],
)
def test_calculate_pace_rejects_ineligible_sets(
    distance_meters: Decimal | None,
    duration_seconds: int | None,
) -> None:
    assert (
        calculate_pace_seconds_per_km(
            distance_meters,
            duration_seconds,
        )
        is None
    )


def test_calculate_decimal_average() -> None:
    result = calculate_decimal_average(
        [
            Decimal("8.0"),
            Decimal("8.5"),
        ]
    )

    assert result == Decimal("8.25")


def test_calculate_decimal_average_returns_none_for_empty_values() -> None:
    assert calculate_decimal_average([]) is None


@pytest.mark.parametrize(
    ("value", "quantum", "expected"),
    [
        (
            Decimal("1.2345"),
            THREE_PLACE_QUANTUM,
            Decimal("1.235"),
        ),
        (
            Decimal("1.2344"),
            THREE_PLACE_QUANTUM,
            Decimal("1.234"),
        ),
        (
            Decimal("123.455"),
            DISTANCE_QUANTUM,
            Decimal("123.46"),
        ),
        (
            Decimal("8.25"),
            RPE_QUANTUM,
            Decimal("8.3"),
        ),
    ],
)
def test_round_decimal_uses_round_half_up(
    value: Decimal,
    quantum: Decimal,
    expected: Decimal,
) -> None:
    assert round_decimal(value, quantum) == expected
