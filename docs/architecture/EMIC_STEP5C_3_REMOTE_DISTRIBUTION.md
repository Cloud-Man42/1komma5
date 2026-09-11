# Step 5C.3 — Remote Distribution

Sprint B adds secure remote artifact acquisition ending at **STAGED / QUARANTINED / REJECTED** only.

## Components

| Package | Responsibility |
|---------|----------------|
| `distribution/catalog_resolver.py` | Resolve releases from TUF trust cache only |
| `distribution/source_precedence.py` | LOCAL > INTERNAL/ORG > PUBLIC precedence |
| `distribution/url_policy.py` | HTTPS, SSRF/DNS, port validation |
| `distribution/downloader.py` | Streaming download, digest verify, cache |
| `distribution/staging_service.py` | Orchestration pipeline (no install) |
| `backend/app/api/marketplace_distribution.py` | Admin fetch/catalog/security API |

## State machine

`DISCOVERED → DOWNLOAD_PENDING → DOWNLOADING → DOWNLOADED → VERIFYING → STAGED | QUARANTINED | REJECTED`

## Forbidden

- `PackageInstaller.install()` from marketplace/distribution layers
- Runtime enable / `sys.path` staging
- Arbitrary client-supplied artifact URLs

See also: [EMIC_REMOTE_ARTIFACT_SECURITY.md](../security/EMIC_REMOTE_ARTIFACT_SECURITY.md)
