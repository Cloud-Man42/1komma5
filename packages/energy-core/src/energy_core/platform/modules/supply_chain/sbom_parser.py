"""Defensive SBOM parsing (CycloneDX + SPDX JSON)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from energy_core.platform.modules.supply_chain.types import ParsedSbom, SbomComponent, SupplyChainError, SupplyChainErrorCode

MAX_SBOM_BYTES = 5_242_880
MAX_COMPONENTS = 10_000
MAX_NESTING = 32


def sbom_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_sbom(raw: bytes, *, expected_digest: str | None = None) -> ParsedSbom:
    if len(raw) > MAX_SBOM_BYTES:
        raise SupplyChainError("SBOM exceeds size limit", code=SupplyChainErrorCode.SBOM_INVALID)
    digest = sbom_digest(raw)
    if expected_digest and digest != expected_digest.lower():
        raise SupplyChainError("SBOM digest mismatch", code=SupplyChainErrorCode.SBOM_DIGEST_MISMATCH)
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SupplyChainError("Malformed SBOM JSON", code=SupplyChainErrorCode.SBOM_INVALID) from exc
    if not isinstance(doc, dict):
        raise SupplyChainError("SBOM root must be object", code=SupplyChainErrorCode.SBOM_INVALID)

    bom_format = doc.get("bomFormat")
    if bom_format == "CycloneDX":
        return _parse_cyclonedx(doc, digest)
    if doc.get("spdxVersion"):
        return _parse_spdx(doc, digest)
    raise SupplyChainError("Unsupported SBOM format", code=SupplyChainErrorCode.SBOM_INVALID)


def _parse_cyclonedx(doc: dict[str, Any], digest: str) -> ParsedSbom:
    spec = str(doc.get("specVersion", "1.0"))
    components_raw = doc.get("components", [])
    if not isinstance(components_raw, list):
        raise SupplyChainError("Invalid components list", code=SupplyChainErrorCode.SBOM_INVALID)
    if len(components_raw) > MAX_COMPONENTS:
        raise SupplyChainError("Too many SBOM components", code=SupplyChainErrorCode.SBOM_INVALID)
    components: list[SbomComponent] = []
    for item in components_raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name:
            continue
        version = item.get("version")
        purl = item.get("purl")
        cpe = None
        for ext in item.get("externalReferences") or []:
            if isinstance(ext, dict) and ext.get("type") == "cpe23Type":
                cpe = ext.get("reference")
        licenses: list[str] = []
        for lic in item.get("licenses") or []:
            if isinstance(lic, dict):
                lic_id = lic.get("license", {}).get("id") if isinstance(lic.get("license"), dict) else lic.get("id")
                if lic_id:
                    licenses.append(str(lic_id))
        hashes = {}
        for h in item.get("hashes") or []:
            if isinstance(h, dict) and h.get("alg") and h.get("content"):
                hashes[str(h["alg"])] = str(h["content"])
        components.append(
            SbomComponent(
                name=name,
                version=str(version) if version is not None else None,
                purl=str(purl) if purl else None,
                cpe=str(cpe) if cpe else None,
                supplier=str(item.get("supplier", {}).get("name")) if isinstance(item.get("supplier"), dict) else None,
                licenses=tuple(licenses),
                hashes=hashes,
            )
        )
    deps: list[tuple[str, str]] = []
    for dep in doc.get("dependencies") or []:
        if isinstance(dep, dict) and dep.get("ref"):
            ref = str(dep["ref"])
            for sub in dep.get("dependsOn") or []:
                deps.append((ref, str(sub)))
    return ParsedSbom(format="CycloneDX", spec_version=spec, components=tuple(components), raw_digest=digest, dependencies=tuple(deps))


def _parse_spdx(doc: dict[str, Any], digest: str) -> ParsedSbom:
    spec = str(doc.get("spdxVersion", "2.0"))
    packages = doc.get("packages", [])
    if not isinstance(packages, list):
        raise SupplyChainError("Invalid SPDX packages", code=SupplyChainErrorCode.SBOM_INVALID)
    components: list[SbomComponent] = []
    for pkg in packages[:MAX_COMPONENTS]:
        if not isinstance(pkg, dict):
            continue
        name = pkg.get("name")
        if not isinstance(name, str):
            continue
        version = pkg.get("versionInfo")
        purl = None
        for ref in pkg.get("externalRefs") or []:
            if isinstance(ref, dict) and ref.get("referenceType") == "purl":
                purl = ref.get("referenceLocator")
        components.append(
            SbomComponent(
                name=name,
                version=str(version) if version else None,
                purl=str(purl) if purl else None,
                licenses=tuple(str(x) for x in (pkg.get("licenseDeclared") or "").split(" AND ") if x),
            )
        )
    return ParsedSbom(format="SPDX", spec_version=spec, components=tuple(components), raw_digest=digest)
