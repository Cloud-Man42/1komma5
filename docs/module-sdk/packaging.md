# Packaging

Canonical `.emicpkg` layout:

```
manifest.json
module/
schemas/configuration.schema.json
migrations/
integrity/checksums.sha256
integrity/signature.json   # Ed25519 (required in production unless EMIC_ALLOW_UNSIGNED_MODULES=true)
```

See [security.md](./security.md) for canonical signing, trust store, and verification details.

Max package size defaults to 50MB (`EMIC_MODULE_PACKAGE_MAX_BYTES`).
