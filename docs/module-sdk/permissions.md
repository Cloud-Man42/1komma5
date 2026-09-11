# Permissions

Declarative permission strings (e.g. `network.external`, `device.control`) are **validated at install time** against the allowlist in `permissions.py`. Unknown permissions return `INVALID_PERMISSION`. Capability/permission coupling is enforced (for example `read_status` requires `device.read`).

Permissions document intent for future policy enforcement and are **not** an OS-level sandbox. See [security.md](./security.md) for the full trust and permission model.
