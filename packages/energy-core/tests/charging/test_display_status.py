"""Tests for Swedish display status labels."""

from energy_core.charging.display_status import display_status_sv
from energy_core.charging.state_machine import SmartChargingState


def test_externally_limited_label():
    assert display_status_sv(state=SmartChargingState.CHARGING_STABLE, reason="cheap_now", externally_limited=True) == "Externt begränsad"


def test_reason_label_smart_wait():
    assert (
        display_status_sv(state=None, reason="smart_wait_cheaper", externally_limited=False)
        == "Väntar på lägre pris"
    )


def test_reason_label_quick_charge():
    assert display_status_sv(state=None, reason="quick_charge", externally_limited=False) == "Snabbladdning"


def test_state_label_reducing():
    assert display_status_sv(state=SmartChargingState.REDUCING, reason=None, externally_limited=False) == "Minskar laddström"
