# Step 5C.4 — SBOM & Advisories

## TUF target

`emic/advisories.json` — monotonic generation, wipe/rollback rejected (mirrors revocation policy).

## Parser & matcher

- `supply_chain/sbom_parser.py` — CycloneDX + SPDX JSON
- `supply_chain/vulnerability_matcher.py` — PURL + semver ranges via `packaging`
- `supply_chain/release_security_evaluator.py` — org policy + governance integration

## Re-evaluation

On advisory sync commit, trust cache updates advisories; staged artifact security snapshots can be re-evaluated (no runtime side effects).
