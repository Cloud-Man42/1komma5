"""Collector-side integration health wiring."""

from __future__ import annotations

from energy_core.integrations.collector_health import record_provider_outcome
from energy_core.integrations.health import IntegrationHealthRecorder

__all__ = ["IntegrationHealthRecorder", "record_provider_outcome"]
