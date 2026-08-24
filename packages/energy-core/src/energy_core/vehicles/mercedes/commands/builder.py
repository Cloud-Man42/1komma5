"""Build Mercedes protobuf command payloads."""

from __future__ import annotations

import uuid

from energy_core.vehicles.mercedes.commands.features import MercedesCommandFeatures
from energy_core.vehicles.mercedes.protocol.proto import client_pb2, vehicle_commands_pb2


def _request_id() -> str:
    return str(uuid.uuid4())


def build_set_target_soc_command(
    *,
    vin: str,
    target_soc_percent: int,
    features: MercedesCommandFeatures,
) -> tuple[bytes, str]:
    """Build target SoC command using mbapi2020-compatible routing."""
    if not features.supports_set_target_soc():
        raise ValueError("Vehicle does not expose a supported target SoC command feature")
    command = vehicle_commands_pb2.CommandRequest()
    command.vin = vin
    request_id = _request_id()
    command.request_id = request_id
    if features.charging_configure:
        max_soc = _clamp_target_soc(target_soc_percent)
        command.charging_configure.max_soc.value = max_soc
    elif features.battery_max_soc_configure:
        command.battery_max_soc.max_soc = _clamp_target_soc(target_soc_percent, minimum=50)
    elif features.charge_program_configure:
        max_soc = _clamp_target_soc(target_soc_percent, minimum=50)
        command.charge_program_configure.max_soc.value = max_soc
        command.charge_program_configure.charge_program = 0
    return _wrap_client_message(command), request_id


def build_charging_action_command(
    *,
    vin: str,
    action: str,
    features: MercedesCommandFeatures,
) -> tuple[bytes, str]:
    """Send charging start/stop using the command surface exposed by Mercedes REST."""
    normalized = action.lower()
    command = vehicle_commands_pb2.CommandRequest()
    command.vin = vin
    request_id = _request_id()
    command.request_id = request_id
    if normalized == "stop":
        if features.charge_coupler_stop:
            command.charge_coupler_stop.SetInParent()
        elif features.charging_configure:
            command.charging_configure.action = vehicle_commands_pb2.ChargingConfigure.STOP
        else:
            raise ValueError("Vehicle does not expose a supported stop-charging command feature")
    elif normalized == "start":
        if not features.charging_configure:
            raise ValueError("Vehicle does not expose CHARGING_CONFIGURE")
        command.charging_configure.action = vehicle_commands_pb2.ChargingConfigure.START
    elif normalized in {"pause", "resume"}:
        if not features.charging_configure:
            raise ValueError("Vehicle does not expose CHARGING_CONFIGURE")
        action_map = {
            "pause": vehicle_commands_pb2.ChargingConfigure.PAUSE,
            "resume": vehicle_commands_pb2.ChargingConfigure.RESUME,
        }
        command.charging_configure.action = action_map[normalized]
    else:
        raise ValueError(f"Unsupported charging action: {action}")
    return _wrap_client_message(command), request_id


def describe_client_message(payload: bytes) -> str:
    """Return a human-readable summary of a serialized ClientMessage."""
    message = client_pb2.ClientMessage()
    message.ParseFromString(payload)
    command = message.commandRequest
    if command.HasField("charging_configure"):
        cfg = command.charging_configure
        parts = ["charging_configure"]
        if cfg.action:
            parts.append(f"action={vehicle_commands_pb2.ChargingConfigure.Action.Name(cfg.action)}")
        if cfg.HasField("max_soc"):
            parts.append(f"max_soc={cfg.max_soc.value}")
        return ", ".join(parts)
    if command.HasField("battery_max_soc"):
        return f"battery_max_soc.max_soc={command.battery_max_soc.max_soc}"
    if command.HasField("charge_program_configure"):
        cfg = command.charge_program_configure
        return f"charge_program_configure program={cfg.charge_program} max_soc={cfg.max_soc.value}"
    if command.HasField("charge_coupler_stop"):
        return "charge_coupler_stop"
    return command.WhichOneof("command") or "unknown"


def _wrap_client_message(command: vehicle_commands_pb2.CommandRequest) -> bytes:
    message = client_pb2.ClientMessage()
    message.tracking_id = _request_id()
    message.commandRequest.CopyFrom(command)
    return message.SerializeToString()


def _clamp_target_soc(value: int, *, minimum: int = 30) -> int:
    return max(minimum, min(100, int(value)))
