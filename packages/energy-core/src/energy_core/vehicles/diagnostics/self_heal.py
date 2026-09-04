"""Evaluate vehicle telemetry health and recommend self-healing actions."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.db.models import VehicleHaloCorrelationModel, VehicleStateLatestModel
from energy_core.vehicles.connection_signals import resolve_effective_connection
from energy_core.vehicles.diagnostics.events import (
    IntegrationEventDraft,
    IntegrationEventSeverity,
    IntegrationEventType,
    SelfHealAction,
    SelfHealResult,
)
from energy_core.vehicles.mercedes.constants import STALE_TELEMETRY_SECONDS


def _age_seconds(timestamp: datetime | None, *, now: datetime) -> float | None:
    if timestamp is None:
        return None
    ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
    return max(0.0, (now - ts).total_seconds())


def evaluate_vehicle_self_heal(
    *,
    latest: VehicleStateLatestModel | None,
    correlation: VehicleHaloCorrelationModel | None = None,
    polling_mode: str | None = None,
    polling_interval_seconds: int | None = None,
    now: datetime | None = None,
) -> SelfHealResult:
    """Detect stale or inconsistent telemetry and decide corrective actions."""
    current = now or datetime.now(UTC)
    if latest is None:
        return SelfHealResult()

    events: list[IntegrationEventDraft] = []
    actions: list[SelfHealAction] = []

    soc_age = _age_seconds(getattr(latest, "soc_updated_at", None), now=current)
    vehicle_age = _age_seconds(latest.last_vehicle_update, now=current)
    charging_age = _age_seconds(getattr(latest, "charging_updated_at", None), now=current)
    range_age = _age_seconds(getattr(latest, "range_updated_at", None), now=current)

    if soc_age is not None and soc_age > STALE_TELEMETRY_SECONDS:
        events.append(
            IntegrationEventDraft(
                event_type=IntegrationEventType.SOC_STALE,
                severity=IntegrationEventSeverity.WARN,
                message=(
                    f"SoC is stale ({int(soc_age)}s old, stored {latest.state_of_charge_percent}%); "
                    "forcing REST refresh"
                ),
                details={
                    "soc_percent": latest.state_of_charge_percent,
                    "soc_age_seconds": round(soc_age, 1),
                    "vehicle_age_seconds": round(vehicle_age, 1) if vehicle_age is not None else None,
                    "charging_age_seconds": round(charging_age, 1) if charging_age is not None else None,
                    "stale_threshold_seconds": STALE_TELEMETRY_SECONDS,
                },
            )
        )
        actions.append(SelfHealAction.FORCE_REST_SYNC)
        if range_age is not None and range_age > STALE_TELEMETRY_SECONDS:
            events.append(
                IntegrationEventDraft(
                    event_type=IntegrationEventType.WS_RECONNECT_REQUESTED,
                    severity=IntegrationEventSeverity.ACTION,
                    message=(
                        "SoC and range both stale at Mercedes source; "
                        "requesting websocket reconnect for live VehicleStatusUpdates"
                    ),
                    details={
                        "soc_age_seconds": round(soc_age, 1),
                        "range_age_seconds": round(range_age, 1),
                    },
                )
            )
            actions.append(SelfHealAction.FORCE_WS_RECONNECT)
    elif (
        soc_age is not None
        and vehicle_age is not None
        and vehicle_age <= 120
        and soc_age > 120
        and latest.state_of_charge_percent is not None
    ):
        events.append(
            IntegrationEventDraft(
                event_type=IntegrationEventType.SOC_NOT_IN_MESSAGE,
                severity=IntegrationEventSeverity.INFO,
                message=(
                    f"Recent vehicle updates ({int(vehicle_age)}s) without fresh SoC "
                    f"(last SoC update {int(soc_age)}s ago at {latest.state_of_charge_percent}%)"
                ),
                details={
                    "soc_percent": latest.state_of_charge_percent,
                    "soc_age_seconds": round(soc_age, 1),
                    "vehicle_age_seconds": round(vehicle_age, 1),
                },
            )
        )

    effective = resolve_effective_connection(
        latest,
        plugged_agreement=correlation.plugged_agreement if correlation else None,
    )
    raw_plugged = latest.is_plugged_in
    raw_charging = latest.is_charging
    if (raw_plugged, raw_charging) != (effective.is_plugged_in, effective.is_charging):
        events.append(
            IntegrationEventDraft(
                event_type=IntegrationEventType.CONNECTION_HEALED,
                severity=IntegrationEventSeverity.INFO,
                message=(
                    "Connection state reconciled: "
                    f"raw plugged={raw_plugged} charging={raw_charging} → "
                    f"effective plugged={effective.is_plugged_in} charging={effective.is_charging}"
                ),
                details={
                    "raw_is_plugged_in": raw_plugged,
                    "raw_is_charging": raw_charging,
                    "effective_is_plugged_in": effective.is_plugged_in,
                    "effective_is_charging": effective.is_charging,
                    "correlation_status": correlation.status if correlation else None,
                    "plugged_agreement": correlation.plugged_agreement if correlation else None,
                },
            )
        )

    if (
        polling_mode
        and (soc_age is not None and soc_age > STALE_TELEMETRY_SECONDS)
    ):
        events.append(
            IntegrationEventDraft(
                event_type=IntegrationEventType.POLLING_MODE,
                severity=IntegrationEventSeverity.INFO,
                message=f"Polling mode {polling_mode} ({polling_interval_seconds or '?'}s)",
                details={
                    "mode": polling_mode,
                    "interval_seconds": polling_interval_seconds,
                    "soc_age_seconds": round(soc_age, 1) if soc_age is not None else None,
                },
            )
        )

    return SelfHealResult(events=tuple(events), actions=tuple(dict.fromkeys(actions)))
