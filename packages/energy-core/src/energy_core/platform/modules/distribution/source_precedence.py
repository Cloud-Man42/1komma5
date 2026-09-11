"""Deterministic artifact source precedence (Step 5C.3)."""

from __future__ import annotations

from energy_core.platform.modules.distribution.types import (
    ArtifactDescriptor,
    ArtifactSourceType,
    DistributionError,
    DistributionErrorCode,
)
from energy_core.platform.modules.packages.paths import is_protected_module_id

_SOURCE_ORDER = {
    ArtifactSourceType.LOCAL: 0,
    ArtifactSourceType.INTERNAL: 1,
    ArtifactSourceType.ORG: 2,
    ArtifactSourceType.PUBLIC: 3,
}


class SourcePrecedenceEngine:
    """Reject namespace shadowing and pick highest-precedence descriptor."""

    def select(self, candidates: list[ArtifactDescriptor]) -> ArtifactDescriptor:
        if not candidates:
            raise DistributionError("No artifact candidates", code=DistributionErrorCode.ARTIFACT_NOT_FOUND)
        for candidate in candidates:
            if is_protected_module_id(candidate.module_id) and candidate.source == ArtifactSourceType.PUBLIC:
                raise DistributionError(
                    f"PUBLIC source cannot shadow protected namespace: {candidate.module_id}",
                    code=DistributionErrorCode.NAMESPACE_SHADOWING,
                )
        return min(candidates, key=lambda c: (_SOURCE_ORDER.get(c.source, 99), c.release_id))
