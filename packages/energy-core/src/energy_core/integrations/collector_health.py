"""Helpers for recording integration health from collector steps."""

from __future__ import annotations

from energy_core.integrations.health import IntegrationHealthRecorder

PROVIDER_LABELS_SV: dict[str, str] = {
    "heartbeat": "Heartbeat",
    "price_engine": "Prismotor",
    "solar_forecast": "Solprognos",
    "arctic_spa": "Arctic Spa",
    "energy_control": "Energistyrning",
    "mercedes": "Mercedes me",
    "chargefinder": "ChargeFinder",
}


def provider_label_sv(provider: str) -> str:
    return PROVIDER_LABELS_SV.get(provider, provider)


async def record_provider_outcome(
    recorder: IntegrationHealthRecorder,
    site_id: int,
    provider: str,
    *,
    success: bool,
    error_class: str | None = None,
    latency_ms: float | None = None,
    circuit_breaker_state: str | None = None,
) -> None:
    if success:
        await recorder.record_success(
            site_id,
            provider,
            latency_ms=latency_ms,
            circuit_breaker_state=circuit_breaker_state,
        )
        return
    await recorder.record_failure(
        site_id,
        provider,
        error_class=error_class or "Error",
        latency_ms=latency_ms,
        circuit_breaker_state=circuit_breaker_state,
    )
