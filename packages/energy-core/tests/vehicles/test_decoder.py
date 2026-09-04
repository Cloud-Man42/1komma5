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


def test_decoder_maps_vehicle_status_rest_payload():
    decoder = MercedesMessageDecoder()
    status_msg = vehicle_events_pb2.VehicleStatus()
    status_msg.vin = "W1KTESTVIN1234567"
    status_msg.attributes["soc"].int_value = 63
    status_msg.attributes["chargingstatus"].string_value = "unplugged"
    mapped = decoder.decode_vehicle_status(status_msg.SerializeToString())
    assert mapped is not None
    assert mapped.vin == "W1KTESTVIN1234567"
    assert any(attr.name == ATTRIBUTE_SOC and attr.value == 63 for attr in mapped.attributes)
    assert any(attr.name == "chargingstatus" and attr.value == "unplugged" for attr in mapped.attributes)


def test_decoder_vehicle_status_returns_none_for_invalid_payload():
    decoder = MercedesMessageDecoder()
    assert decoder.decode_vehicle_status(b"not-protobuf") is None


def test_decoder_prefers_display_value_for_chargingstatus():
    decoder = MercedesMessageDecoder()
    status_msg = vehicle_events_pb2.VehicleStatus()
    status_msg.vin = "W1KTESTVIN1234567"
    status_msg.attributes["chargingstatus"].int_value = 8
    status_msg.attributes["chargingstatus"].display_value = "Not charging"
    mapped = decoder.decode_vehicle_status(status_msg.SerializeToString())
    assert mapped is not None
    assert any(attr.name == "chargingstatus" and attr.value == "Not charging" for attr in mapped.attributes)


def test_decoder_prefers_display_soc_when_it_diverges_from_int():
    decoder = MercedesMessageDecoder()
    status_msg = vehicle_events_pb2.VehicleStatus()
    status_msg.vin = "W1KTESTVIN1234567"
    status_msg.attributes["soc"].int_value = 31
    status_msg.attributes["soc"].display_value = "37 %"
    mapped = decoder.decode_vehicle_status(status_msg.SerializeToString())
    assert mapped is not None
    assert any(attr.name == ATTRIBUTE_SOC and attr.value == 37.0 for attr in mapped.attributes)


def test_decoder_vehicle_status_update_prefers_display_soc():
    decoder = MercedesMessageDecoder()
    update = vehicle_events_pb2.VehicleStatusUpdate()
    update.fin_or_vin = "W1KTESTVIN1234567"
    update.soc.value = 31
    update.soc.display_value = "37 %"
    mapped = decoder.decode_vehicle_status(update.SerializeToString())
    assert mapped is not None
    assert any(attr.name == ATTRIBUTE_SOC and attr.value == 37.0 for attr in mapped.attributes)


def test_decoder_maps_vehicle_status_update_rest_payload():
    decoder = MercedesMessageDecoder()
    update = vehicle_events_pb2.VehicleStatusUpdate()
    update.fin_or_vin = "W1KTESTVIN1234567"
    update.soc.value = 27
    update.position_lat.value = 57.2610544
    update.position_long.value = 16.4806263
    update.rangeelectric.value = 113
    mapped = decoder.decode_vehicle_status(update.SerializeToString())
    assert mapped is not None
    assert mapped.vin == "W1KTESTVIN1234567"
    assert any(attr.name == ATTRIBUTE_SOC and attr.value == 27 for attr in mapped.attributes)
    assert any(attr.name == "positionlat" and attr.value == 57.2610544 for attr in mapped.attributes)
    assert any(attr.name == "positionlong" and attr.value == 16.4806263 for attr in mapped.attributes)
    assert any(attr.name == "rangeelectrickm" and attr.value == 113 for attr in mapped.attributes)


def test_decoder_skips_unavailable_vehicle_status_update_fields():
    decoder = MercedesMessageDecoder()
    update = vehicle_events_pb2.VehicleStatusUpdate()
    update.fin_or_vin = "W1KTESTVIN1234567"
    update.rangeliquid.metadata.status = 4
    mapped = decoder.decode_vehicle_status(update.SerializeToString())
    assert mapped is not None
    assert mapped.attributes == ()


def test_decoder_reads_display_value_when_numeric_oneof_unset():
    decoder = MercedesMessageDecoder()
    status_msg = vehicle_events_pb2.VehicleStatus()
    status_msg.vin = "W1KTESTVIN1234567"
    status_msg.attributes["chargingstatus"].display_value = "Unplugged"
    mapped = decoder.decode_vehicle_status(status_msg.SerializeToString())
    assert mapped is not None
    assert any(attr.name == "chargingstatus" and attr.value == "Unplugged" for attr in mapped.attributes)
