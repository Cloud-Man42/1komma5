"""Mercedes command response parser tests."""

from __future__ import annotations

from energy_core.vehicles.mercedes.commands.response import parse_command_status
from energy_core.vehicles.mercedes.protocol.proto import vehicle_events_pb2, vehicleapi_pb2


def test_parse_command_status_returns_matching_request():
    push = vehicle_events_pb2.PushMessage()
    updates = push.apptwin_command_status_updates_by_vin
    by_vin = updates.updates_by_vin["W1KTESTVIN0000001"]
    status = by_vin.updates_by_pid[42]
    status.request_id = "req-123"
    status.state = 5  # FINISHED
    status.type = 1
    parsed = parse_command_status(push.SerializeToString())
    assert parsed is not None
    assert parsed.request_id == "req-123"
    assert parsed.state == "FINISHED"
    assert parsed.type_name == "1"
