"""Arctic Spa API models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def fahrenheit_to_celsius(value: float | int | None) -> float | None:
    if value is None:
        return None
    return round((float(value) - 32.0) * 5.0 / 9.0, 2)


def celsius_to_fahrenheit_int(value_c: float) -> int:
    """Quantize to whole Fahrenheit for Arctic Spa setpoint API."""
    return int(round(value_c * 9.0 / 5.0 + 32.0))


HEATER_FILTER_STATUSES = frozenset({"Filtering", "Boost", "Resuming", "Overtemperature", "Sanitize", "Purge"})
HEATER_ELEMENT_STATUSES = frozenset({"Boost", "Resuming", "Overtemperature", "Sanitize"})


@dataclass(frozen=True, slots=True)
class ArcticSpaStatus:
    connected: bool
    temperature_c: float | None
    setpoint_c: float | None
    lights: str | None
    pump1: str | None
    pump2: str | None
    pump3: str | None
    pump4: str | None
    pump5: str | None
    filter_status: str | None
    filter_duration: int | None
    filter_frequency: float | None
    filter_suspension: bool | None
    errors: tuple[str, ...] = ()
    blower1: str | None = None
    blower2: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> ArcticSpaStatus:
        errors = payload.get("errors") or []
        if not isinstance(errors, list):
            errors = []
        return cls(
            connected=bool(payload.get("connected")),
            temperature_c=fahrenheit_to_celsius(payload.get("temperatureF")),
            setpoint_c=fahrenheit_to_celsius(payload.get("setpointF")),
            lights=_str_or_none(payload.get("lights")),
            pump1=_str_or_none(payload.get("pump1")),
            pump2=_str_or_none(payload.get("pump2")),
            pump3=_str_or_none(payload.get("pump3")),
            pump4=_str_or_none(payload.get("pump4")),
            pump5=_str_or_none(payload.get("pump5")),
            filter_status=_str_or_none(payload.get("filter_status")),
            filter_duration=_int_or_none(payload.get("filter_duration")),
            filter_frequency=_float_or_none(payload.get("filter_frequency")),
            filter_suspension=_bool_or_none(payload.get("filter_suspension")),
            errors=tuple(str(e) for e in errors),
            blower1=_str_or_none(payload.get("blower1")),
            blower2=_str_or_none(payload.get("blower2")),
            raw=payload,
        )

    @property
    def filter_cycle_active(self) -> bool:
        return self.filter_status in HEATER_FILTER_STATUSES

    @property
    def heater_active(self) -> bool:
        """True when the heating element is expected to draw significant power."""
        return self.heater_element_active

    @property
    def heater_element_active(self) -> bool:
        if self.filter_status in HEATER_ELEMENT_STATUSES:
            return True
        if self.temperature_c is not None and self.setpoint_c is not None:
            return self.temperature_c < self.setpoint_c - 0.5
        return False

    @property
    def pump_states(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for name in ("pump1", "pump2", "pump3", "pump4", "pump5"):
            value = getattr(self, name)
            if value:
                result[name] = value
        return result

    @property
    def primary_pump_label(self) -> str:
        for name, state in self.pump_states.items():
            if state and state != "off":
                return f"{name.replace('pump', 'Pump ')}: {state.capitalize()}"
        return "Pump: Av"


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return bool(value)
