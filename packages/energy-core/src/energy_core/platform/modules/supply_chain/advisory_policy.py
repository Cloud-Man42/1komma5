"""Trusted advisory bundle validation (Step 5C.4)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from energy_core.platform.modules.marketplace.types import MetadataErrorCode
from energy_core.platform.modules.supply_chain.types import AdvisoryEntry, SecuritySeverity


class AdvisoryPolicyError(Exception):
    def __init__(self, message: str, *, error_code: MetadataErrorCode) -> None:
        super().__init__(message)
        self.error_code = error_code


WITHDRAWN = "WITHDRAWN"
SUPERSEDE = "SUPERSEDE"


@dataclass(frozen=True, slots=True)
class AdvisoryBundle:
    generation: int
    generated_at: str
    advisories: tuple[AdvisoryEntry, ...]
    content_hash: str


def bundle_content_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_advisory_bundle(raw: dict[str, Any] | None) -> AdvisoryBundle:
    if raw is None:
        raise AdvisoryPolicyError("Missing advisory bundle", error_code=MetadataErrorCode.INVALID_METADATA)
    bundle_meta = raw.get("bundle")
    if not isinstance(bundle_meta, dict):
        raise AdvisoryPolicyError("Invalid advisory bundle header", error_code=MetadataErrorCode.INVALID_METADATA)
    generation = bundle_meta.get("generation")
    if not isinstance(generation, int) or generation < 1:
        raise AdvisoryPolicyError("Invalid advisory generation", error_code=MetadataErrorCode.INVALID_METADATA)
    generated_at = bundle_meta.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at:
        raise AdvisoryPolicyError("Invalid advisory generated_at", error_code=MetadataErrorCode.INVALID_METADATA)
    entries_raw = raw.get("advisories", [])
    if not isinstance(entries_raw, list):
        raise AdvisoryPolicyError("Invalid advisories list", error_code=MetadataErrorCode.INVALID_METADATA)

    entries: list[AdvisoryEntry] = []
    for item in entries_raw:
        if not isinstance(item, dict):
            continue
        advisory_id = item.get("advisory_id")
        if not isinstance(advisory_id, str) or not advisory_id:
            continue
        status = str(item.get("status", "ACTIVE")).upper()
        withdrawn = status == WITHDRAWN or bool(item.get("withdrawn", False))
        sev_raw = str(item.get("severity", "UNKNOWN")).upper()
        try:
            severity = SecuritySeverity(sev_raw)
        except ValueError:
            severity = SecuritySeverity.UNKNOWN
        affected = item.get("affected") or {}
        if not isinstance(affected, dict):
            affected = {}
        fixed = item.get("fixed_versions") or affected.get("fixed_versions") or []
        if not isinstance(fixed, list):
            fixed = []
        entries.append(
            AdvisoryEntry(
                advisory_id=advisory_id,
                source=str(item.get("source", "emic")),
                severity=severity,
                published_at=item.get("published_at"),
                updated_at=item.get("updated_at"),
                status=status,
                affected_purl=affected.get("purl") or item.get("affected_purl"),
                affected_package=affected.get("package") or item.get("affected_package"),
                affected_version_range=affected.get("version_range") or item.get("affected_version_range"),
                fixed_versions=tuple(str(v) for v in fixed),
                references=tuple(str(r) for r in (item.get("references") or []) if r),
                withdrawn=withdrawn,
            )
        )
    content_hash = bundle_content_hash(raw)
    return AdvisoryBundle(generation=generation, generated_at=generated_at, advisories=tuple(entries), content_hash=content_hash)


def validate_advisory_monotonicity(
    *,
    trusted_generation: int | None,
    trusted_hash: str | None,
    incoming: AdvisoryBundle,
) -> None:
    if trusted_generation is None:
        return
    if incoming.generation < trusted_generation:
        raise AdvisoryPolicyError(
            f"Advisory rollback: {incoming.generation} < {trusted_generation}",
            error_code=MetadataErrorCode.METADATA_ROLLBACK_DETECTED,
        )
    if incoming.generation == trusted_generation and trusted_hash and incoming.content_hash != trusted_hash:
        raise AdvisoryPolicyError(
            "Advisory generation unchanged but content hash differs",
            error_code=MetadataErrorCode.INVALID_METADATA,
        )
    if incoming.generation > trusted_generation and len(incoming.advisories) == 0:
        raise AdvisoryPolicyError(
            "Advisory wipe rejected: empty bundle with higher generation",
            error_code=MetadataErrorCode.INVALID_METADATA,
        )


def _advisory_to_dict(entry: AdvisoryEntry) -> dict[str, Any]:
    return {
        "advisory_id": entry.advisory_id,
        "severity": entry.severity.value,
        "status": entry.status,
        "source": entry.source,
        "withdrawn": entry.withdrawn,
        "affected": {
            "purl": entry.affected_purl,
            "package": entry.affected_package,
            "version_range": entry.affected_version_range,
            "fixed_versions": list(entry.fixed_versions),
        },
    }


def merge_advisory_bundles(
    *,
    trusted_raw: dict[str, Any] | None,
    incoming: AdvisoryBundle,
    incoming_raw: dict[str, Any],
) -> dict[str, Any]:
    """Conservative merge: active advisories persist unless explicitly withdrawn/superseded."""
    active: dict[str, dict[str, Any]] = {}
    if trusted_raw is not None:
        try:
            trusted = parse_advisory_bundle(trusted_raw)
        except AdvisoryPolicyError:
            trusted = None
        else:
            for entry in trusted.advisories:
                if not entry.withdrawn and entry.status.upper() != WITHDRAWN:
                    active[entry.advisory_id] = _advisory_to_dict(entry)

    incoming_ids = {entry.advisory_id for entry in incoming.advisories}
    for entry in incoming.advisories:
        status = entry.status.upper()
        if status == WITHDRAWN or entry.withdrawn:
            active.pop(entry.advisory_id, None)
            continue
        if status == SUPERSEDE:
            supersede_id = getattr(entry, "supersedes_advisory_id", None)
            if isinstance(supersede_id, str):
                active.pop(supersede_id, None)
        active[entry.advisory_id] = _advisory_to_dict(entry)

    merged_entries = sorted(active.values(), key=lambda item: item["advisory_id"])
    return {
        "bundle": {
            "generation": incoming.generation,
            "generated_at": incoming.generated_at,
        },
        "advisories": merged_entries,
    }
