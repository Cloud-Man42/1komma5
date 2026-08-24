"""Mercedes protobuf decoder tests."""

from __future__ import annotations

from energy_core.vehicles.mercedes.constants import ATTRIBUTE_SOC
from energy_core.vehicles.mercedes.protocol.decoder import MercedesMessageDecoder
from energy_core.vehicles.mercedes.protocol.proto import vehicle_events_pb2


def test_decoder_returns_none_for_invalid_payload():
    decoder = MercedesMessageDecoder()
    assert decoder.decode(b"not-protobuf") is None
    assert decoder.decode_failures == 1


def test_decoder_returns_none_for_empty_push_message():
    decoder = MercedesMessageDecoder()
    message = vehicle_events_pb2.PushMessage()
    assert decoder.decode(message.SerializeToString()) is None


def test_decoder_maps_vehicle_status_updates():
    decoder = MercedesMessageDecoder()
    push = vehicle_events_pb2.PushMessage()
    entry = push.vehicle_status_updates.vehicle_status_updates["W1KTEST"]
    entry.fin_or_vin = "W1KTESTVIN1234567"
    entry.soc.value = 72
    mapped = decoder.decode(push.SerializeToString())
    assert mapped is not None
    assert mapped.vin == "W1KTESTVIN1234567"
    assert any(attr.name == ATTRIBUTE_SOC and attr.value == 72 for attr in mapped.attributes)


def test_decoder_maps_vep_update_attributes():
    decoder = MercedesMessageDecoder()
    update = vehicle_events_pb2.VEPUpdate()
    update.vin = "W1KTESTVIN1234567"
    status = update.attributes["soc"]
    status.int_value = 55
    mapped = decoder.decode_vep_update(update.SerializeToString())
    assert mapped is not None
    assert mapped.vin == "W1KTESTVIN1234567"
    assert any(attr.name == ATTRIBUTE_SOC and attr.value == 55 for attr in mapped.attributes)
