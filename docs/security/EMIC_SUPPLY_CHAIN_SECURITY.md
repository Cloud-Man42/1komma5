# Supply-Chain Security (Step 5C.4)

## Trusted advisories

- TUF target `emic/advisories.json` with monotonic generation (rollback/wipe rejected)
- Persisted in trust cache + normalized advisory tables

## SBOM

- CycloneDX JSON primary; SPDX JSON optional
- Embedded in `.emicpkg` or trusted external ref from catalog (`sbom_ref` + digest)

## Evaluation

`ReleaseSecurityEvaluator` combines SBOM status, advisory matches, org `supply_chain_policy_json`, and governance decision.

Integrity snapshot (per digest) is separate from current supply-chain risk (re-evaluated on advisory sync).

## Policy extensions

`module_installation_policy.supply_chain_policy_json`:

- `require_sbom`
- `deny_critical_vulnerabilities`
- `max_allowed_severity`
- `require_review_for_high`
