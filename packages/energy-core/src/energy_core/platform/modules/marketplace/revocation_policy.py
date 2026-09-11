"""Revocation bundle validation and monotonic merge (Step 5C.1.5)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from energy_core.platform.modules.marketplace.types import MetadataErrorCode


class RevocationPolicyError(Exception):
    """Revocation bundle rejected by policy."""

    def __init__(self, message: str, *, error_code: MetadataErrorCode) -> None:
        super().__init__(message)
        self.error_code = error_code


REVOKE_ACTION = "REVOKE"
SUPERSEDE_ACTION = "SUPERSEDE"


@dataclass(frozen=True, slots=True)
class RevocationEntry:
    revocation_id: str
    scope: str
    publisher_id: str | None
    module_id: str | None
    version: str | None
    artifact_hash: str | None
    reason: str | None
    severity: str | None
    effective_at: str | None
    action: str
    supersedes_revocation_id: str | None


@dataclass(frozen=True, slots=True)
class RevocationBundle:
    schema_version: int
    generation: int
    generated_at: str
    revocations: tuple[RevocationEntry, ...]
    content_hash: str


def bundle_content_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_revocation_bundle(raw: dict[str, Any] | None) -> RevocationBundle:
    if raw is None:
        raise RevocationPolicyError("Missing revocation bundle", error_code=MetadataErrorCode.INVALID_METADATA)
    bundle_meta = raw.get("bundle")
    if not isinstance(bundle_meta, dict):
        raise RevocationPolicyError("Invalid revocation bundle header", error_code=MetadataErrorCode.INVALID_METADATA)
    generation = bundle_meta.get("generation")
    if not isinstance(generation, int) or generation < 1:
        raise RevocationPolicyError("Invalid revocation generation", error_code=MetadataErrorCode.INVALID_METADATA)
    schema_version = bundle_meta.get("schema_version", 1)
    if not isinstance(schema_version, int):
        raise RevocationPolicyError("Invalid revocation schema_version", error_code=MetadataErrorCode.INVALID_METADATA)
    generated_at = bundle_meta.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at:
        raise RevocationPolicyError("Invalid revocation generated_at", error_code=MetadataErrorCode.INVALID_METADATA)
    entries_raw = raw.get("revocations")
    if entries_raw is None:
        entries_raw = []
    if not isinstance(entries_raw, list):
        raise RevocationPolicyError("Invalid revocations list", error_code=MetadataErrorCode.INVALID_METADATA)

    entries: list[RevocationEntry] = []
    for item in entries_raw:
        if not isinstance(item, dict):
            raise RevocationPolicyError("Invalid revocation entry", error_code=MetadataErrorCode.INVALID_METADATA)
        revocation_id = item.get("revocation_id")
        if not isinstance(revocation_id, str) or not revocation_id:
            raise RevocationPolicyError("Missing revocation_id", error_code=MetadataErrorCode.INVALID_METADATA)
        action = str(item.get("action", REVOKE_ACTION)).upper()
        if action not in {REVOKE_ACTION, SUPERSEDE_ACTION}:
            raise RevocationPolicyError(f"Invalid revocation action: {action}", error_code=MetadataErrorCode.INVALID_METADATA)
        supersedes = item.get("supersedes_revocation_id")
        if action == SUPERSEDE_ACTION and (not isinstance(supersedes, str) or not supersedes):
            raise RevocationPolicyError(
                "SUPERSEDE requires supersedes_revocation_id",
                error_code=MetadataErrorCode.INVALID_METADATA,
            )
        entries.append(
            RevocationEntry(
                revocation_id=revocation_id,
                scope=str(item.get("scope", "global")),
                publisher_id=item.get("publisher_id"),
                module_id=item.get("module_id"),
                version=item.get("version"),
                artifact_hash=item.get("artifact_hash"),
                reason=item.get("reason"),
                severity=item.get("severity"),
                effective_at=item.get("effective_at"),
                action=action,
                supersedes_revocation_id=supersedes if isinstance(supersedes, str) else None,
            )
        )

    content_hash = bundle_content_hash(raw)
    return RevocationBundle(
        schema_version=schema_version,
        generation=generation,
        generated_at=generated_at,
        revocations=tuple(entries),
        content_hash=content_hash,
    )


def validate_revocation_monotonicity(
    *,
    trusted_generation: int | None,
    trusted_hash: str | None,
    incoming: RevocationBundle,
) -> None:
    if trusted_generation is None:
        return
    if incoming.generation < trusted_generation:
        raise RevocationPolicyError(
            f"Revocation generation rollback {incoming.generation} < {trusted_generation}",
            error_code=MetadataErrorCode.METADATA_ROLLBACK_DETECTED,
        )
    if incoming.generation == trusted_generation and trusted_hash and incoming.content_hash != trusted_hash:
        raise RevocationPolicyError(
            f"Revocation generation {incoming.generation} content mutation detected",
            error_code=MetadataErrorCode.INVALID_METADATA,
        )


def merge_revocation_bundles(
    *,
    trusted_raw: dict[str, Any] | None,
    incoming: RevocationBundle,
    incoming_raw: dict[str, Any],
) -> dict[str, Any]:
    """Conservative merge: active revocations persist unless explicitly superseded."""
    active: dict[str, dict[str, Any]] = {}
    if trusted_raw is not None:
        try:
            trusted = parse_revocation_bundle(trusted_raw)
        except RevocationPolicyError:
            trusted = None
        else:
            for entry in trusted.revocations:
                if entry.action == REVOKE_ACTION:
                    active[entry.revocation_id] = _entry_to_dict(entry)

    for entry in incoming.revocations:
        if entry.action == SUPERSEDE_ACTION and entry.supersedes_revocation_id:
            active.pop(entry.supersedes_revocation_id, None)
            continue
        if entry.action == REVOKE_ACTION:
            active[entry.revocation_id] = _entry_to_dict(entry)

    merged_revocations = sorted(active.values(), key=lambda item: item["revocation_id"])
    merged: dict[str, Any] = {
        "bundle": {
            "schema_version": incoming.schema_version,
            "generation": incoming.generation,
            "generated_at": incoming.generated_at,
        },
        "revocations": merged_revocations,
    }
    return merged


def revocations_changed(
    *,
    before_raw: dict[str, Any] | None,
    after_raw: dict[str, Any] | None,
) -> bool:
    if before_raw is None and after_raw is None:
        return False
    if before_raw is None or after_raw is None:
        return True
    return bundle_content_hash(before_raw) != bundle_content_hash(after_raw)


def _entry_to_dict(entry: RevocationEntry) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "revocation_id": entry.revocation_id,
        "scope": entry.scope,
        "action": entry.action,
    }
    for key in (
        "publisher_id",
        "module_id",
        "version",
        "artifact_hash",
        "reason",
        "severity",
        "effective_at",
        "supersedes_revocation_id",
    ):
        value = getattr(entry, key)
        if value is not None:
            payload[key] = value
    return payload
