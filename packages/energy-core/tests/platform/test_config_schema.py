"""Tests for module configuration schema validation."""

from energy_core.platform.modules.config_schema import mask_config_for_response, validate_config_values

SCHEMA = {
    "fields": [
        {"name": "host", "label": "Host", "type": "string", "required": True},
        {"name": "api_key", "label": "API key", "type": "secret", "secret": True, "required": True},
    ]
}


def test_validate_config_flags_missing_required():
    errors = validate_config_values(SCHEMA, {})
    assert "host" in errors
    assert "api_key" in errors


def test_validate_config_accepts_configured_secret():
    errors = validate_config_values(SCHEMA, {"host": "example"}, configured_secrets={"api_key"})
    assert errors == {}


def test_mask_config_hides_secret_values():
    public, configured = mask_config_for_response(
        SCHEMA,
        {"host": "example", "api_key": "secret"},
        configured_secrets={"api_key"},
    )
    assert public == {"host": "example"}
    assert configured["api_key"] is True
    assert "api_key" not in public
