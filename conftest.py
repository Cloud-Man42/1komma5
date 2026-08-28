"""Repo-wide test guards."""

from __future__ import annotations

import pytest


class OutboundNetworkBlocked(RuntimeError):
    """A test tried to reach a live service instead of a fake."""


def _message(url: object) -> str:
    return (
        f"Outbound request to {url} blocked. Mock the client or provider instead, "
        "or mark the test with @pytest.mark.integration if it truly needs the network."
    )


@pytest.fixture(autouse=True)
def block_outbound_http(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail fast on real HTTP calls so a networkless runner cannot be the first to notice.

    Only the transports that open sockets are patched, so httpx ASGITransport and
    MockTransport keep working for in-process API tests.
    """
    if "integration" in request.keywords:
        return

    def blocked_httpx(_self: object, http_request: object, *_args: object, **_kwargs: object):
        raise OutboundNetworkBlocked(_message(getattr(http_request, "url", "unknown URL")))

    monkeypatch.setattr("httpx.AsyncHTTPTransport.handle_async_request", blocked_httpx)
    monkeypatch.setattr("httpx.HTTPTransport.handle_request", blocked_httpx)

    try:
        import requests.adapters
    except ImportError:
        return

    def blocked_requests(_self: object, prepared: object, *_args: object, **_kwargs: object):
        raise OutboundNetworkBlocked(_message(getattr(prepared, "url", "unknown URL")))

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", blocked_requests)


@pytest.fixture(autouse=True)
def mock_dmi_harmonie_forecast(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return stable DMI point forecasts without live HTTP in unit tests."""

    async def fake_fetch_rows(_self, **kwargs):
        from datetime import UTC, datetime, timedelta

        start = kwargs.get("from_ts") or datetime.now(UTC)
        rows = []
        for hour in range(0, 49):
            ts = start + timedelta(hours=hour)
            rows.append(
                {
                    "ts_utc": ts,
                    "ghi_wm2": max(0.0, 500.0 - abs(hour - 12) * 25.0),
                    "dhi_wm2": 120.0,
                    "temperature_c": 18.0,
                    "cloud_cover_pct": 25.0,
                    "humidity_pct": 70.0,
                    "wind_speed_ms": 4.0,
                    "precipitation_mm": 0.0,
                }
            )
        to_ts = kwargs.get("to_ts")
        if to_ts is not None:
            rows = [row for row in rows if row["ts_utc"] <= to_ts]
        return rows

    monkeypatch.setattr(
        "energy_core.solar_intelligence.providers.dmi_harmonie.DmiHarmonieClient.fetch_rows",
        fake_fetch_rows,
    )
