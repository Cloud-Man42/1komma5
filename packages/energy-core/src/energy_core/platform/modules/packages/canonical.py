"""Canonical serialization for package signing and integrity."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_manifest_bytes(raw: dict[str, Any]) -> bytes:
    payload = dict(raw)
    payload.pop("integrity", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def manifest_sha256(raw: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_manifest_bytes(raw)).hexdigest()


def signing_digest(*, content_sha256: str, manifest_sha256_hex: str) -> bytes:
    return f"{content_sha256}\n{manifest_sha256_hex}".encode("utf-8")
