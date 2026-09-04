"""Tests for collector integration health helpers."""

from __future__ import annotations

import pytest

from energy_core.integrations.collector_health import provider_label_sv, record_provider_outcome


def test_provider_label_sv_maps_known_providers() -> None:
    assert provider_label_sv("price_engine") == "Prismotor"
    assert provider_label_sv("unknown") == "unknown"


@pytest.mark.asyncio
async def test_record_provider_outcome_success() -> None:
    calls: list[tuple[str, tuple, dict]] = []

    class FakeRecorder:
        async def record_success(self, site_id, provider, **kwargs):
            calls.append(("success", (site_id, provider), kwargs))

        async def record_failure(self, site_id, provider, **kwargs):
            calls.append(("failure", (site_id, provider), kwargs))

    await record_provider_outcome(FakeRecorder(), 1, "heartbeat", success=True, latency_ms=12.5)
    assert calls == [("success", (1, "heartbeat"), {"latency_ms": 12.5, "circuit_breaker_state": None})]


@pytest.mark.asyncio
async def test_record_provider_outcome_failure() -> None:
    calls: list[tuple[str, tuple, dict]] = []

    class FakeRecorder:
        async def record_success(self, site_id, provider, **kwargs):
            calls.append(("success", (site_id, provider), kwargs))

        async def record_failure(self, site_id, provider, **kwargs):
            calls.append(("failure", (site_id, provider), kwargs))

    await record_provider_outcome(
        FakeRecorder(),
        2,
        "solar_forecast",
        success=False,
        error_class="TimeoutError",
    )
    assert calls[0][0] == "failure"
    assert calls[0][1] == (2, "solar_forecast")
    assert calls[0][2]["error_class"] == "TimeoutError"
