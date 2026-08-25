"""Redact sensitive values from Heartbeat API payloads and headers."""

from __future__ import annotations

import re
from typing import Any

SENSITIVE_HEADER_NAMES = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
    }
)

SENSITIVE_KEY_PATTERN = re.compile(
    r"(token|password|secret|authorization|refresh|session|client_secret|api_key|bearer)",
    re.IGNORECASE,
)

REDACTED = "***REDACTED***"


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADER_NAMES or SENSITIVE_KEY_PATTERN.search(key):
            result[key] = REDACTED
        else:
            result[key] = value
    return result


def redact_json(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            key: REDACTED if SENSITIVE_KEY_PATTERN.search(str(key)) else redact_json(value)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [redact_json(item) for item in data]
    if isinstance(data, str) and len(data) > 64 and SENSITIVE_KEY_PATTERN.search(data):
        return REDACTED
    return data


def contains_credential_leak(text: str) -> bool:
    lowered = text.lower()
    if "bearer " in lowered and "***" not in text:
        return True
    if re.search(r'"password"\s*:\s*"[^*]', text):
        return True
    return False
