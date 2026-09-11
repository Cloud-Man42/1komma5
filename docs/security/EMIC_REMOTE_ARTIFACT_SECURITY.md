# Remote Artifact Security

## SSRF defenses

- HTTPS required in production; test localhost HTTP allowed only when `APP_ENV != production`
- Resolve DNS before connect; reject RFC1918, loopback (PUBLIC), link-local, metadata IP `169.254.169.254`
- No redirects by default; bounded HTTPS-only redirects when explicitly enabled
- No embedded credentials; forbidden schemes (`file://`, `data:`, etc.)

## Integrity

- Streaming SHA-256 during download
- Size limits (`MARKETPLACE_ARTIFACT_MAX_BYTES`) enforced via Content-Length and stream
- Cache reuse re-validates digest before staging
- `PackageValidator.validate_archive()` static validation only

## Identity

Catalog descriptor must match manifest module/version/publisher; protected namespaces cannot be shadowed from PUBLIC catalog.
