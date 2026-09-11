# Module package security

Step 5A.5 adds cryptographic trust, integrity revalidation, and honest permission policy for EMIC module packages.

## Trust model

| Publisher class | Meaning |
| --- | --- |
| Internal publisher | Key in EMIC trust store (`module_publisher_keys` table or read-only config) |
| Trusted third-party publisher | Same as internal; explicitly registered |
| Unknown publisher | Not in trust store — install blocked in production |

Package trust is **not** implied by a valid manifest. Separate flags apply:

- `valid` — manifest/structure/compatibility checks passed
- `signed` — `integrity/signature.json` present
- `signature_valid` — Ed25519 verification succeeded
- `publisher_trusted` — signing key is trusted and not revoked
- `install_allowed` — policy allows install (signed+trusted, or dev unsigned override)

## Signing

### Signed payload

EMIC signs and verifies a digest of:

```text
{content_sha256}\n{manifest_sha256}
```

- **content_sha256** — SHA-256 over sorted archive members (UTF-8 path + NUL + bytes). `manifest.json` is hashed with the `integrity` field removed using canonical JSON. `integrity/signature.json` is excluded from the content hash.
- **manifest_sha256** — SHA-256 over canonical manifest JSON (`integrity` removed, sorted keys, compact separators, UTF-8).

### Canonicalization

```text
UTF-8
json.dumps(payload, sort_keys=True, separators=(",", ":"))
integrity field stripped before hashing/signing
normalized archive member paths (POSIX)
```

### signature.json

```json
{
  "algorithm": "ed25519",
  "publisher": "emic-tests",
  "key_id": "test-1",
  "content_sha256": "...",
  "manifest_sha256": "...",
  "signature": "<base64>"
}
```

Verification uses the `cryptography` library (Ed25519). Invalid signatures return `SIGNATURE_INVALID`.

## Publisher keys

Trust store fields:

- `publisher_id`
- `key_id`
- `public_key_hex`
- `status` — `trusted`, `revoked`, or `disabled`

Key rotation uses `publisher_id + key_id`. Revoked or unknown keys reject install.

**Private publisher keys must never be stored in EMIC runtime configuration, container images, or this repository.** Use them only in CI/build tooling.

## Unsigned policy

- Default: `EMIC_ALLOW_UNSIGNED_MODULES=false` (fail-secure)
- Dev/test may set `EMIC_ALLOW_UNSIGNED_MODULES=true`
- Production installs require a valid signature from a trusted publisher

## Integrity at install and startup

Install/update validates content and manifest hashes plus signature/trust.

On backend/collector startup, `load_installed_module_packages()` revalidates every installed package. Tampering, checksum mismatch, or invalid signature moves the package to `QUARANTINED` and skips registry load.

## Permissions

Permissions are **validated at install** against an allowlist. They are **not** OS-level sandbox enforcement.

Allowlist includes: `network.external`, `network.local`, `device.read`, `device.control`, `vehicle.location`, `filesystem.module_data`, `secrets.read_own`.

Control capabilities require `device.control`. Read capabilities such as `read_status` require `device.read`.

Unknown permissions return `INVALID_PERMISSION`.

## Package states

- `INSTALLED` — healthy, loadable
- `QUARANTINED` — integrity/signature/load failure; cannot enable or register capabilities
- `BROKEN` — update/rollback failure
- `REMOVING` — remove in progress

Quarantine metadata includes `quarantine_reason`, `quarantined_at`, `last_error`, and `detected_version`.

## Archive safety

Upload size limit, max entry count, max uncompressed size, compression ratio guard, and path traversal rejection apply during validation/extract.

## Updates

- Default downgrade blocked (`VERSION_DOWNGRADE_NOT_ALLOWED`); explicit `allow_downgrade=true` + admin auth for rollback-style downgrades
- Major updates require migration scripts under `migrations/`
- Failed health-gated updates roll back only after promotion; pre-promote health failures leave the current version active
- Concurrent mutations serialized per `module_id` via `PackageMutationLock`

## Remove safety

Remove is blocked when the module is enabled on sites, depended on by other modules, or owns registered devices (`MODULE_HAS_DEVICES`). Historical telemetry is retained.
