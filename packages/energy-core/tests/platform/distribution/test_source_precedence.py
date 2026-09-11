"""Source precedence tests."""

from __future__ import annotations

import pytest

from energy_core.platform.modules.distribution.source_precedence import SourcePrecedenceEngine
from energy_core.platform.modules.distribution.types import (
    ArtifactDescriptor,
    ArtifactSourceType,
    DistributionError,
    DistributionErrorCode,
)


def _desc(source: ArtifactSourceType, release_id: str = "r1") -> ArtifactDescriptor:
    return ArtifactDescriptor(
        module_id="integration.demo",
        publisher_id="emic-tests",
        version="1.0.0",
        release_id=release_id,
        artifact_url="http://127.0.0.1/pkg.emicpkg",
        content_sha256="a" * 64,
        artifact_size=100,
        source=source,
    )


def test_local_beats_public():
    selected = SourcePrecedenceEngine().select([_desc(ArtifactSourceType.PUBLIC), _desc(ArtifactSourceType.LOCAL, "local")])
    assert selected.source == ArtifactSourceType.LOCAL


def test_public_shadowing_protected_namespace():
    desc = ArtifactDescriptor(
        module_id="core.demo",
        publisher_id="evil",
        version="1.0.0",
        release_id="r1",
        artifact_url="http://127.0.0.1/pkg.emicpkg",
        content_sha256="b" * 64,
        artifact_size=100,
        source=ArtifactSourceType.PUBLIC,
    )
    with pytest.raises(DistributionError) as exc:
        SourcePrecedenceEngine().select([desc])
    assert exc.value.code == DistributionErrorCode.NAMESPACE_SHADOWING
