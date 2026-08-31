"""Tests for Mercedes attribute observer masking."""

from __future__ import annotations

from energy_core.vehicles.mercedes.mapping.observer import (
    MercedesAttributeRecorder,
    mask_attribute_value,
)
from energy_core.vehicles.mercedes.protocol.decoder import MercedesAttributeUpdate, MercedesPushMessage


def test_mask_coordinate_rounds_to_two_decimals():
    assert mask_attribute_value("positionLat", 55.6123456) == "~55.61"
    assert mask_attribute_value("positionLong", 13.123456) == "~13.12"


def test_mask_vin_and_sensitive_names():
    vin17 = "W1K12345678901234"
    assert mask_attribute_value("fin", vin17) == "<redacted>"
    assert mask_attribute_value("display_value", vin17) == "W1K1…1234"
    assert mask_attribute_value("email", "user@example.com") == "<redacted>"


def test_recorder_drains_observations():
    recorder = MercedesAttributeRecorder()
    message = MercedesPushMessage(
        attributes=(
            MercedesAttributeUpdate(name="soc", value=72),
            MercedesAttributeUpdate(name="positionLat", value=55.61),
        ),
        vin="W1K1234567890ABCDE",
    )
    recorder.observe_message(message, source="WS")
    drained = recorder.drain()
    assert len(drained) == 2
    assert drained[0].attribute_name == "soc"
    assert drained[0].masked_sample == "72"
    assert drained[1].attribute_name == "positionlat"
    assert drained[1].masked_sample == "~55.61"
    assert recorder.drain() == []
