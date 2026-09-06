"""Vendor-neutral attribute observation records for field discovery."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AttributeObservation:
    attribute_name: str
    source: str
    value_type: str
    masked_sample: str
