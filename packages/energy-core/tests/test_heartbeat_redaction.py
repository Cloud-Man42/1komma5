"""Tests for Heartbeat secret redaction."""

from energy_core.integrations.heartbeat.redaction import (
    REDACTED,
    redact_headers,
    redact_observation_payload,
    redact_string,
)


def test_redact_string_masks_bearer() -> None:
    assert "secret" not in redact_string("Authorization: Bearer abc123")
    assert REDACTED in redact_string("Authorization: Bearer abc123")


def test_redact_headers_masks_authorization() -> None:
    result = redact_headers({"Authorization": "Bearer x", "Accept": "application/json"})
    assert result["Authorization"] == REDACTED
    assert result["Accept"] == "application/json"


def test_redact_observation_payload_masks_sensitive_keys() -> None:
    payload = {
        "systemId": "uuid-1",
        "password": "mathias3",
        "nested": {"accessToken": "tok", "serialNumber": "K183-600-000-021-000-P-X"},
    }
    result = redact_observation_payload(payload)
    assert result["password"] == REDACTED
    assert result["nested"]["accessToken"] == REDACTED
    assert result["nested"]["serialNumber"] == "K183-600-000-021-000-P-X"
    assert result["systemId"] == "uuid-1"
