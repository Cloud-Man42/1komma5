"""Observe and mask Mercedes attribute names/values for field discovery."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

_SENSITIVE_NAME_PARTS = (
    "vin",
    "fin",
    "email",
    "phone",
    "name",
    "address",
    "token",
    "password",
    "credential",
)
_COORDINATE_NAMES = frozenset(
    {
        "positionlat",
        "positionlong",
        "positionheading",
        "latitude",
        "longitude",
        "heading",
        "gpslat",
        "gpslong",
    }
)


@dataclass(frozen=True, slots=True)
class AttributeObservation:
    attribute_name: str
    source: str
    value_type: str
    masked_sample: str


class MercedesAttributeRecorder:
    """Records attribute names and masked samples without storing raw secrets."""

    def __init__(self) -> None:
        self._pending: list[AttributeObservation] = []

    def observe(self, *, name: str, value: Any, source: str) -> None:
        normalized = name.strip().lower()
        if not normalized:
            return
        self._pending.append(
            AttributeObservation(
                attribute_name=normalized,
                source=source,
                value_type=_value_type(value),
                masked_sample=mask_attribute_value(normalized, value),
            )
        )

    def observe_message(self, message: Any, *, source: str) -> None:
        for attr in getattr(message, "attributes", ()) or ():
            self.observe(name=attr.name, value=attr.value, source=source)

    def drain(self) -> list[AttributeObservation]:
        items = list(self._pending)
        self._pending.clear()
        return items


def _value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    return type(value).__name__


def mask_attribute_value(name: str, value: Any) -> str:
    normalized = name.strip().lower()
    if value is None:
        return "<null>"
    if _is_sensitive_name(normalized):
        return "<redacted>"
    if normalized in _COORDINATE_NAMES or "position" in normalized:
        return _mask_coordinate(value)
    if normalized == "soc" or normalized.endswith("soc"):
        return _mask_numeric(value, decimals=0)
    if "power" in normalized or normalized.endswith("kw"):
        return _mask_numeric(value, decimals=1)
    if "range" in normalized or normalized.endswith("km"):
        return _mask_numeric(value, decimals=0)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return _mask_numeric(value, decimals=2)
    text = str(value)
    if len(text) > 64:
        return f"{text[:32]}…<{len(text)} chars>"
    if _looks_like_vin(text):
        return _mask_vin(text)
    return text


def _is_sensitive_name(name: str) -> bool:
    return any(part in name for part in _SENSITIVE_NAME_PARTS)


def _mask_coordinate(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "<coord>"
    rounded = round(numeric, 2)
    return f"~{rounded:.2f}"


def _mask_numeric(value: Any, *, decimals: int) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if decimals == 0:
        return str(int(round(numeric)))
    return f"{numeric:.{decimals}f}"


def _looks_like_vin(text: str) -> bool:
    cleaned = text.strip().upper()
    return len(cleaned) == 17 and re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", cleaned) is not None


def _mask_vin(vin: str) -> str:
    cleaned = vin.strip().upper()
    if len(cleaned) < 8:
        return "<vin>"
    return f"{cleaned[:4]}…{cleaned[-4:]}"


def observation_now() -> datetime:
    return datetime.now(UTC)
