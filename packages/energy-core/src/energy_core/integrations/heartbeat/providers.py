"""Backend provider kinds for Heartbeat / GridX installations."""

from __future__ import annotations

from enum import StrEnum


class HeartbeatBackendProvider(StrEnum):
    ONEKOMMAFIVE = "1komma5"
    GRIDX = "gridx"
