"""Sanitize Heartbeat payloads and log lines — never expose secrets."""

from __future__ import annotations

import re
from typing import Any

REDACTED = "***REDACTED***"

_SENSITIVE_KEY = re.compile(
    r"(token|password|secret|authorization|cookie|session|api[_-]?key|refresh|bearer|gridxstartcode|credential|gridxStartCode)",
    re.IGNORECASE,
)
_SENSITIVE_HEADER = re.compile(
    r"(authorization|cookie|set-cookie|x-api-key)",
    re.IGNORECASE,
)
_BEARER = re.compile(r"Bearer\s+\S+", re.IGNORECASE)


def is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY.search(key))


def redact_string(value: str) -> str:
    if not value:
        return value
    redacted = _BEARER.sub(f"Bearer {REDACTED}", value)
    if len(redacted) > 48 and redacted == value:
        return REDACTED
    return redacted


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in headers.items():
        if _SENSITIVE_HEADER.search(key):
            result[key] = REDACTED
        else:
            result[key] = redact_string(value)
    return result


def sanitize_mapping(data: dict[str, Any], *, max_depth: int = 8) -> dict[str, Any]:
    return _sanitize(data, depth=0, max_depth=max_depth)


def redact_observation_payload(data: dict[str, Any]) -> dict[str, Any]:
    return sanitize_mapping(data)


def _sanitize(value: Any, *, depth: int, max_depth: int) -> Any:
    if depth > max_depth:
        return "…"
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_str = str(key)
            if is_sensitive_key(key_str):
                out[key_str] = REDACTED
            else:
                out[key_str] = _sanitize(item, depth=depth + 1, max_depth=max_depth)
        return out
    if isinstance(value, list):
        return [_sanitize(item, depth=depth + 1, max_depth=max_depth) for item in value[:50]]
    if isinstance(value, str):
        return redact_string(value)
    return value
