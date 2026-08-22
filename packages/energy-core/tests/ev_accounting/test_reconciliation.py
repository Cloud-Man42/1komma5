"""Tests for SessionReconciliationService (H)."""

from energy_core.ev_accounting.models import EnergyAttribution
from energy_core.ev_accounting.reconciliation import SessionReconciliationService


def test_h_reconciliation_scales_to_meter():
    service = SessionReconciliationService()
    attr = EnergyAttribution(solar_direct_kwh=10.0, grid_direct_kwh=11.8)
    result = service.reconcile(attr, measured_kwh=22.0, attributed_kwh=21.8)
    assert abs(result.attribution.total_kwh - 22.0) < 0.01
    assert result.note == "scaled_to_meter"
