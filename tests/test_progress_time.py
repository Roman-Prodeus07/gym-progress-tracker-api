from datetime import UTC, date, datetime, timedelta

import pytest

from app.schemas.progress import ProgressBucket
from app.services.progress_time import (
    build_bucket_starts,
    local_date_range_to_utc,
)


def test_local_date_range_uses_inclusive_dates_and_exclusive_end() -> None:
    result = local_date_range_to_utc(
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 2),
        timezone_name="UTC",
    )

    assert result.start_inclusive == datetime(2026, 1, 1, tzinfo=UTC)
    assert result.end_exclusive == datetime(2026, 1, 3, tzinfo=UTC)


def test_local_date_range_handles_spring_dst_transition() -> None:
    result = local_date_range_to_utc(
        date_from=date(2026, 3, 29),
        date_to=date(2026, 3, 29),
        timezone_name="Europe/London",
    )

    assert result.start_inclusive == datetime(2026, 3, 29, tzinfo=UTC)
    assert result.end_exclusive == datetime(2026, 3, 29, 23, 0, tzinfo=UTC)
    assert result.end_exclusive - result.start_inclusive == timedelta(hours=23)


def test_local_date_range_handles_autumn_dst_transition() -> None:
    result = local_date_range_to_utc(
        date_from=date(2026, 10, 25),
        date_to=date(2026, 10, 25),
        timezone_name="Europe/London",
    )

    assert result.start_inclusive == datetime(2026, 10, 24, 23, 0, tzinfo=UTC)
    assert result.end_exclusive == datetime(2026, 10, 26, tzinfo=UTC)
    assert result.end_exclusive - result.start_inclusive == timedelta(hours=25)


@pytest.mark.parametrize(
    ("bucket", "date_from", "date_to", "expected"),
    [
        (
            ProgressBucket.DAY,
            date(2026, 4, 1),
            date(2026, 4, 3),
            (
                date(2026, 4, 1),
                date(2026, 4, 2),
                date(2026, 4, 3),
            ),
        ),
        (
            ProgressBucket.WEEK,
            date(2026, 4, 1),
            date(2026, 4, 14),
            (
                date(2026, 3, 30),
                date(2026, 4, 6),
                date(2026, 4, 13),
            ),
        ),
        (
            ProgressBucket.MONTH,
            date(2026, 12, 15),
            date(2027, 2, 2),
            (
                date(2026, 12, 1),
                date(2027, 1, 1),
                date(2027, 2, 1),
            ),
        ),
    ],
)
def test_build_bucket_starts_uses_local_calendar_boundaries(
    bucket: ProgressBucket,
    date_from: date,
    date_to: date,
    expected: tuple[date, ...],
) -> None:
    assert build_bucket_starts(date_from, date_to, bucket) == expected


def test_build_bucket_starts_rejects_reversed_dates() -> None:
    with pytest.raises(
        ValueError,
        match="date_from cannot be later than date_to",
    ):
        build_bucket_starts(
            date_from=date(2026, 2, 1),
            date_to=date(2026, 1, 31),
            bucket=ProgressBucket.DAY,
        )
