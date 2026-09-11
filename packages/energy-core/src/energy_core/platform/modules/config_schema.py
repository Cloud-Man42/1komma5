"""Module configuration schema validation (vendor-neutral)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ConfigFieldSchema:
    name: str
    label: str
    field_type: str
    required: bool = False
    secret: bool = False
    advanced: bool = False
    help_text: str = ""
    default: Any = None
    options: tuple[str, ...] = ()


def parse_configuration_schema(raw: dict[str, Any]) -> tuple[ConfigFieldSchema, ...]:
    fields_raw = raw.get("fields") if isinstance(raw, dict) else None
    if not isinstance(fields_raw, list):
        return ()
    fields: list[ConfigFieldSchema] = []
    for item in fields_raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        options_raw = item.get("options")
        options = tuple(str(opt) for opt in options_raw) if isinstance(options_raw, list) else ()
        fields.append(
            ConfigFieldSchema(
                name=name,
                label=str(item.get("label") or name),
                field_type=str(item.get("type") or "string"),
                required=bool(item.get("required", False)),
                secret=bool(item.get("secret", False)),
                advanced=bool(item.get("advanced", False)),
                help_text=str(item.get("help") or ""),
                default=item.get("default"),
                options=options,
            )
        )
    return tuple(fields)


def validate_config_values(
    schema: dict[str, Any],
    values: dict[str, Any],
    *,
    configured_secrets: set[str] | None = None,
) -> dict[str, str]:
    """Return field-level validation errors (empty dict means valid)."""
    configured_secrets = configured_secrets or set()
    errors: dict[str, str] = {}
    for field in parse_configuration_schema(schema):
        raw = values.get(field.name)
        if field.secret:
            if raw not in (None, "") or field.name in configured_secrets:
                continue
            if field.required:
                errors[field.name] = "Required secret is not configured"
            continue
        if raw is None or raw == "":
            if field.required and field.default is None:
                errors[field.name] = "Required field is missing"
            continue
        if field.field_type == "integer":
            try:
                int(raw)
            except (TypeError, ValueError):
                errors[field.name] = "Must be an integer"
        if field.options and str(raw) not in field.options:
            errors[field.name] = "Invalid option"
    return errors


def mask_config_for_response(
    schema: dict[str, Any],
    values: dict[str, Any],
    *,
    configured_secrets: set[str] | None = None,
) -> tuple[dict[str, Any], dict[str, bool]]:
    configured_secrets = configured_secrets or set()
    public: dict[str, Any] = {}
    configured_fields: dict[str, bool] = {}
    for field in parse_configuration_schema(schema):
        if field.secret:
            configured_fields[field.name] = field.name in configured_secrets or bool(values.get(field.name))
            continue
        if field.name in values:
            public[field.name] = values[field.name]
            configured_fields[field.name] = values[field.name] not in (None, "")
        elif field.default is not None:
            public[field.name] = field.default
            configured_fields[field.name] = True
        else:
            configured_fields[field.name] = False
    return public, configured_fields
