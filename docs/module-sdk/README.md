# EMIC Module SDK

Step 5A introduces the `.emicpkg` package format and SDK contracts for third-party modules.

## Key points

- Packages are ZIP archives validated and installed locally (no Store UI in 5A).
- Activation is **restart-based** — install/update/rollback/remove set `restart_required=true`.
- Permissions are declarative policy metadata, not an OS sandbox.
- Built-in modules (`integration.*`, `feature.*` bootstrap set) cannot be replaced via package API.

## Docs

- [Getting started](getting-started.md)
- [Manifest](manifest.md)
- [Lifecycle](lifecycle.md)
- [Capabilities](capabilities.md)
- [Configuration](configuration.md)
- [Health](health.md)
- [Permissions](permissions.md)
- [Packaging](packaging.md)
- [Versioning](versioning.md)
- [Testing](testing.md)
