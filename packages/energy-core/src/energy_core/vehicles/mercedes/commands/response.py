"""Parse Mercedes command status responses from websocket frames."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from google.protobuf.message import DecodeError

from energy_core.vehicles.mercedes.protocol.proto import vehicle_events_pb2


@dataclass(frozen=True, slots=True)
class MercedesCommandStatus:
    request_id: str
    state: str
    type_name: str = ""
    error_code: str = ""
    error_message: str = ""


def parse_command_status(payload: bytes) -> MercedesCommandStatus | None:
    try:
        message = vehicle_events_pb2.PushMessage()
        message.ParseFromString(payload)
    except (DecodeError, TypeError):
        return None
    msg_type = message.WhichOneof("msg")
    if msg_type != "apptwin_command_status_updates_by_vin":
        return None
    updates = message.apptwin_command_status_updates_by_vin
    for _vin, by_pid in updates.updates_by_vin.items():
        for _pid, status in by_pid.updates_by_pid.items():
            return MercedesCommandStatus(
                request_id=str(status.request_id or ""),
                state=_command_state_name(status),
                type_name=str(status.type or ""),
                error_code=_format_errors(status),
                error_message=_format_errors(status),
            )
    return None


def _command_state_name(status: Any) -> str:
    if hasattr(status, "state"):
        value = status.state
        if hasattr(value, "name"):
            return str(value.name)
        descriptor = status.DESCRIPTOR.fields_by_name.get("state")
        if descriptor is not None and descriptor.enum_type is not None:
            enum_value = descriptor.enum_type.values_by_number.get(int(value))
            if enum_value is not None:
                return enum_value.name
        if value not in (None, 0):
            return str(value)
    return "UNKNOWN"


def _format_errors(status: Any) -> str:
    errors = getattr(status, "errors", None)
    if not errors:
        return ""
    return "; ".join(str(item) for item in errors)
