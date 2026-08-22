"""Fuse diagnostic wiring for bridge-status."""

from datetime import UTC, datetime

from energy_core.charging.engine import bridge_status_from_charger
from energy_core.charging.fuse_diagnostic import fuse_headroom_a_for_charger
from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.energy.state import EnergyState


def _charger(**overrides) -> EvChargerModel:
    charger = EvChargerModel(
        id=1,
        site_id=1,
        name="Halo",
        max_grid_import_w=11000.0,
    )
    for key, value in overrides.items():
        setattr(charger, key, value)
    return charger


def _site(**overrides) -> SiteModel:
    site = SiteModel(slug="akarp", name="Åkarp", timezone="Europe/Stockholm", main_fuse_a=25.0)
    for key, value in overrides.items():
        setattr(site, key, value)
    return site


def test_fuse_headroom_with_main_fuse_only():
    headroom = fuse_headroom_a_for_charger(_charger(), _site())
    assert headroom == 23.0


def test_fuse_headroom_with_phase_currents():
    headroom = fuse_headroom_a_for_charger(
        _charger(),
        _site(),
        phase_current_l1_a=10.0,
        phase_current_l2_a=8.0,
        phase_current_l3_a=12.0,
    )
    assert headroom == 11.0


def test_bridge_status_from_charger_includes_fuse_headroom():
    status = bridge_status_from_charger(_charger(), site=_site())
    assert status.fuse_headroom_a == 23.0


def test_bridge_status_uses_energy_grid_import_for_fuse():
    energy = EnergyState(
        timestamp=datetime.now(UTC),
        grid_import_w=9000.0,
    )
    status = bridge_status_from_charger(_charger(max_current_a=16.0, phases=3), site=_site(), energy=energy)
    assert status.fuse_headroom_a is not None
    assert status.fuse_headroom_a < 23.0
