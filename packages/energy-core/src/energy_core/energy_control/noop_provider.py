"""Default dry-run control provider — no external writes."""

from __future__ import annotations

from energy_core.energy_control.provider import IEnergyControlProvider
from energy_core.energy_control.types import ControlOutcome, ControlResult, ControlTarget, OptimizationAction


class NoopControlProvider:
    provider_name = "noop-dry-run"

    async def apply_action(
        self,
        *,
        site_id: int,
        action: OptimizationAction,
        target: ControlTarget,
        dry_run: bool,
        context: dict | None = None,
    ) -> ControlResult:
        outcome = ControlOutcome.PREVIEW if dry_run else ControlOutcome.APPLIED
        return ControlResult(
            action=action,
            target=target,
            outcome=outcome,
            dry_run=dry_run,
            reason=f"Noop provider recorded {action.value} for site {site_id} (no external writes).",
            reason_sv=f"Noop-provider loggade {action.value} för site {site_id} (inga externa skrivningar).",
            provider=self.provider_name,
            payload={"site_id": site_id, "context": context or {}},
        )


def default_control_provider() -> IEnergyControlProvider:
    from energy_core.energy_control.provider_factory import resolve_control_provider

    return resolve_control_provider()
