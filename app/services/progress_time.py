from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.schemas.progress import ProgressBucket


@dataclass(frozen=True, slots=True)
class UTCDateRange:
    start_inclusive: datetime
    end_exclusive: datetime


def local_date_range_to_utc(
    date_from: date,
    date_to: date,
    timezone_name: str,
) -> UTCDateRange:
    if date_from > date_to:
        raise ValueError("date_from cannot be later than date_to.")

    local_timezone = ZoneInfo(timezone_name)

    local_start = datetime.combine(
        date_from,
        time.min,
        tzinfo=local_timezone,
    )
    local_end = datetime.combine(
        date_to + timedelta(days=1),
        time.min,
        tzinfo=local_timezone,
    )

    return UTCDateRange(
        start_inclusive=local_start.astimezone(UTC),
        end_exclusive=local_end.astimezone(UTC),
    )


def get_bucket_start(
    value: date,
    bucket: ProgressBucket,
) -> date:
    if bucket is ProgressBucket.DAY:
        return value

    if bucket is ProgressBucket.WEEK:
        return value - timedelta(days=value.weekday())

    if bucket is ProgressBucket.MONTH:
        return value.replace(day=1)

    raise ValueError("Unsupported progress bucket.")


def get_next_bucket_start(
    value: date,
    bucket: ProgressBucket,
) -> date:
    if bucket is ProgressBucket.DAY:
        return value + timedelta(days=1)

    if bucket is ProgressBucket.WEEK:
        return value + timedelta(days=7)

    if bucket is ProgressBucket.MONTH:
        if value.month == 12:
            return date(value.year + 1, 1, 1)

        return date(value.year, value.month + 1, 1)

    raise ValueError("Unsupported progress bucket.")


def build_bucket_starts(
    date_from: date,
    date_to: date,
    bucket: ProgressBucket,
) -> tuple[date, ...]:
    if date_from > date_to:
        raise ValueError("date_from cannot be later than date_to.")

    current = get_bucket_start(date_from, bucket)
    final = get_bucket_start(date_to, bucket)
    bucket_starts: list[date] = []

    while current <= final:
        bucket_starts.append(current)
        current = get_next_bucket_start(current, bucket)

    return tuple(bucket_starts)
