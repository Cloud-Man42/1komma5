"""Tests for SessionReconciliationService (H)."""

from energy_core.ev_accounting.models import EnergyAttribution
from energy_core.ev_accounting.reconciliation import SessionReconciliationService


def test_h_reconciliation_scales_to_meter():
    service = SessionReconciliationService()
    attr = EnergyAttribution(solar_direct_kwh=10.0, grid_direct_kwh=11.8)
    result = service.reconcile(attr, measured_kwh=22.0, attributed_kwh=21.8)
    assert abs(result.attribution.total_kwh - 22.0) < 0.01
    assert result.note == "scaled_to_meter"


def test_a_zero_meter_reading_does_not_erase_measured_intervals():
    """Regression: the register resets on unplug, which zeroed real sessions.

    A 23 h session had 886 intervals summing to 75.66 kWh and 151 kr of cost,
    but stop-minus-start read 0, so the attribution was scaled to nothing. The
    dashboard then showed 0.0 kWh, 151 kr, and fell back to labelling it grid.
    """
    service = SessionReconciliationService()
    attr = EnergyAttribution(
        solar_direct_kwh=0.08,
        solar_battery_kwh=0.0,
        grid_battery_kwh=0.05,
        grid_direct_kwh=75.54,
    )

    result = service.reconcile(attr, measured_kwh=0.0, attributed_kwh=75.66)

    assert abs(result.attribution.total_kwh - 75.67) < 0.01
    assert result.attribution.solar_direct_kwh == 0.08
    assert result.attribution.grid_direct_kwh == 75.54
    assert result.note == "meter_register_reset"
    # The intervals are the evidence here, so the total is no longer "MEASURED".
    assert result.energy_quality == "ESTIMATED"
    # The delta is still reported, so the discrepancy stays visible.
    assert abs(result.delta_kwh + 75.66) < 0.01


def test_a_genuinely_empty_session_stays_at_zero():
    """Plugged in but never charged must not be inflated into energy."""
    service = SessionReconciliationService()

    result = service.reconcile(EnergyAttribution(), measured_kwh=0.0, attributed_kwh=0.0)

    assert result.attribution.total_kwh == 0.0
    assert result.note == "within_tolerance"
    assert result.energy_quality == "MEASURED"


def test_a_meter_below_the_intervals_still_wins_when_plausible():
    """A lower but positive meter total is the billing truth, so it scales."""
    service = SessionReconciliationService()
    attr = EnergyAttribution(solar_direct_kwh=10.0, grid_direct_kwh=30.0)

    result = service.reconcile(attr, measured_kwh=24.0, attributed_kwh=40.0)

    assert abs(result.attribution.total_kwh - 24.0) < 0.01
    assert result.note == "scaled_to_meter"
    assert result.energy_quality == "MEASURED"


def test_a_zero_meter_with_noise_level_intervals_is_left_alone():
    """Below tolerance there is nothing worth rescuing, so zero stands."""
    service = SessionReconciliationService()

    result = service.reconcile(
        EnergyAttribution(grid_direct_kwh=0.01),
        measured_kwh=0.0,
        attributed_kwh=0.01,
    )

    assert result.note == "within_tolerance"
    assert result.energy_quality == "MEASURED"


def test_a_missing_meter_reading_keeps_the_attribution():
    service = SessionReconciliationService()
    attr = EnergyAttribution(solar_direct_kwh=5.0, grid_direct_kwh=5.0)

    result = service.reconcile(attr, measured_kwh=None, attributed_kwh=10.0)

    assert result.attribution.total_kwh == 10.0
    assert result.note == "no_meter_reading"
    assert result.energy_quality == "ESTIMATED"
