"""Tests for spa cleaning actuator."""

from datetime import UTC, datetime, timedelta

import pytest

from energy_core.db.spa_control_repo import SpaControlConfigRecord
from energy_core.flexible_load.types import LoadPlan, LoadStrategy, PlanWindow
from energy_core.integrations.arctic_spa.models import ArcticSpaStatus
from energy_core.spa_energy.actuator import SpaCleaningActuator
from energy_core.spa_energy.runtime import SpaActuatorRuntime, SpaActuatorState


def _control(**kwargs) -> SpaControlConfigRecord:
    defaults = dict(
        consumer_id=1,
        smart_control_enabled=True,
        strategy="SMART",
        dry_run=True,
        shadow_mode=False,
        shadow_mode_until=None,
        min_cleaning_hours_per_day=2.0,
        allowed_window_start="07:00",
        allowed_window_end="22:00",
        prefer_solar=True,
        allow_battery=True,
        min_battery_soc_pct=40.0,
        min_run_minutes=30,
        min_stop_minutes=20,
        max_starts_per_day=4,
        filter_cycles_per_day=4,
        filter_duration_minutes=120,
        minimum_cycle_separation_minutes=60,
        filter_optimization_enabled=True,
        last_known_safe_filter_schedule_json=None,
        safety_floor_frequency_per_day=4.0,
        safety_floor_duration_hours=2.0,
        smart_preheat_enabled=False,
        normal_temperature_c=38.0,
        max_preheat_temperature_c=39.0,
        min_comfort_temperature_c=37.0,
        load_priority=50,
        fixed_schedule_start=None,
        fixed_schedule_end=None,
    )
    defaults.update(kwargs)
    return SpaControlConfigRecord(**defaults)


class FakeControlService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def ensure_safety_floor(self, **kwargs) -> None:
        self.calls.append("floor")

    async def start_filtering(self) -> None:
        self.calls.append("start")

    async def stop_filtering(self) -> None:
        self.calls.append("stop")

    async def set_target_temperature_c(self, temperature_c: float) -> None:
        self.calls.append(f"temp:{temperature_c}")


@pytest.mark.asyncio
async def test_actuator_skips_auto_commands_for_fixed_schedule():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    window = PlanWindow(
        start=now,
        end=now + timedelta(hours=2),
        duration=timedelta(hours=2),
        expected_energy_kwh=3.0,
        expected_cost_sek=1.0,
        expected_energy_source=__import__("energy_core.flexible_load.types", fromlist=["EnergySource"]).EnergySource.SOLAR,
        average_score=10.0,
    )
    plan = LoadPlan(
        load_id="spa_cleaning",
        strategy=LoadStrategy.FIXED_SCHEDULE,
        windows=(window,),
        reason="fixed_schedule",
        reason_sv="fast_schema",
        explanation_sv="test",
    )
    runtime = SpaActuatorRuntime()
    actuator = SpaCleaningActuator(
        control=_control(
            dry_run=False,
            strategy="FIXED_SCHEDULE",
            fixed_schedule_start="07:00",
            fixed_schedule_end="22:00",
        ),
        runtime=runtime,
        timezone="Europe/Stockholm",
    )
    fake = FakeControlService()
    decision = await actuator.run_cycle(
        control_service=fake,  # type: ignore[arg-type]
        status=ArcticSpaStatus.from_api({"connected": True, "filter_status": "Idle"}),
        plan=plan,
        now=now,
    )
    assert decision.reason == "spa_self_managed"
    assert fake.calls == []


@pytest.mark.asyncio
async def test_actuator_dry_run_does_not_call_api():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    window = PlanWindow(
        start=now,
        end=now + timedelta(hours=2),
        duration=timedelta(hours=2),
        expected_energy_kwh=3.0,
        expected_cost_sek=1.0,
        expected_energy_source=__import__("energy_core.flexible_load.types", fromlist=["EnergySource"]).EnergySource.SOLAR,
        average_score=10.0,
    )
    plan = LoadPlan(
        load_id="spa_cleaning",
        strategy=LoadStrategy.SMART,
        windows=(window,),
        reason="solar_surplus",
        reason_sv="sol",
        explanation_sv="test",
    )
    runtime = SpaActuatorRuntime()
    actuator = SpaCleaningActuator(control=_control(dry_run=True), runtime=runtime, timezone="Europe/Stockholm")
    fake = FakeControlService()
    decision = await actuator.run_cycle(
        control_service=fake,  # type: ignore[arg-type]
        status=None,
        plan=plan,
        now=now,
    )
    assert decision.dry_run is True
    assert fake.calls == []


@pytest.mark.asyncio
async def test_manual_override_in_dry_run():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    runtime = SpaActuatorRuntime()
    actuator = SpaCleaningActuator(control=_control(dry_run=True), runtime=runtime, timezone="Europe/Stockholm")
    fake = FakeControlService()
    decision = await actuator.run_cycle(
        control_service=fake,  # type: ignore[arg-type]
        status=ArcticSpaStatus.from_api({"connected": True, "filter_status": "Idle"}),
        plan=None,
        now=now,
        manual_override=True,
    )
    assert decision.reason == "manual_override"
    assert decision.dry_run is True
    assert fake.calls == []
    assert runtime.state == SpaActuatorState.WAITING


@pytest.mark.asyncio
async def test_manual_override_bypasses_shadow_mode():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    runtime = SpaActuatorRuntime()
    actuator = SpaCleaningActuator(
        control=_control(dry_run=False, shadow_mode=True),
        runtime=runtime,
        timezone="Europe/Stockholm",
    )
    fake = FakeControlService()
    decision = await actuator.run_cycle(
        control_service=fake,  # type: ignore[arg-type]
        status=ArcticSpaStatus.from_api({"connected": True, "filter_status": "Idle"}),
        plan=None,
        now=now,
        manual_override=True,
    )
    assert decision.reason == "manual_override"
    assert decision.command_sent is True
    assert fake.calls == ["floor", "start"]
    assert runtime.state == SpaActuatorState.CLEANING
