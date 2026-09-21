from datetime import UTC, datetime, timedelta, timezone

import pytest

from travel_status_alerter.schedule import should_run


def utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def test_runs_at_0700_utc_in_winter_gmt() -> None:
    assert should_run(utc(2026, 1, 12, 7, 5))


def test_skips_0600_utc_in_winter_gmt() -> None:
    assert not should_run(utc(2026, 1, 12, 6, 5))


def test_runs_at_0600_utc_in_summer_bst() -> None:
    assert should_run(utc(2026, 7, 13, 6, 5))


def test_skips_0700_utc_in_summer_bst() -> None:
    assert not should_run(utc(2026, 7, 13, 7, 5))


def test_whole_07_hour_local_time_is_accepted() -> None:
    assert should_run(utc(2026, 1, 12, 7, 0))
    assert should_run(utc(2026, 1, 12, 7, 59))
    assert not should_run(utc(2026, 1, 12, 8, 0))


def test_exactly_one_of_the_two_crons_fires_across_the_year() -> None:
    day = utc(2026, 1, 1, 0)
    for offset in range(365):
        date = day + timedelta(days=offset)
        fired = [should_run(date.replace(hour=hour, minute=1)) for hour in (6, 7)]
        assert fired.count(True) == 1, date


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        # Clocks go forward on 2026-03-29 (01:00 UTC): Sunday morning, but the guard is
        # purely about the hour so this checks the boundary is handled correctly.
        (utc(2026, 3, 29, 6, 30), True),
        (utc(2026, 3, 29, 7, 30), False),
        # Clocks go back on 2026-10-25 (01:00 UTC).
        (utc(2026, 10, 25, 6, 30), False),
        (utc(2026, 10, 25, 7, 30), True),
    ],
)
def test_dst_changeover_days(moment: datetime, expected: bool) -> None:
    assert should_run(moment) is expected


def test_accepts_aware_datetimes_in_other_zones() -> None:
    plus_two = timezone(timedelta(hours=2))

    assert should_run(datetime(2026, 1, 12, 9, 15, tzinfo=plus_two))


def test_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        should_run(datetime(2026, 1, 12, 7, 0))
