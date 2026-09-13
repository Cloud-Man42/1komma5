from datetime import UTC, datetime

from energy_core.auth.datetime_utils import ensure_utc, utc_now


def test_ensure_utc_naive_treated_as_utc():
    naive = datetime(2026, 1, 1, 12, 0, 0)
    result = ensure_utc(naive)
    assert result.tzinfo is UTC
    assert result.hour == 12


def test_ensure_utc_aware_converts_to_utc():
    aware = datetime(2026, 1, 1, 13, 0, 0, tzinfo=UTC)
    assert ensure_utc(aware) == aware


def test_utc_now_is_timezone_aware():
    now = utc_now()
    assert now.tzinfo is UTC
