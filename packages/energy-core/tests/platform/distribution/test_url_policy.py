"""URL policy and SSRF tests."""

from __future__ import annotations

import pytest

from energy_core.platform.modules.distribution.types import ArtifactSourceType, DistributionError, DistributionErrorCode
from energy_core.platform.modules.distribution.url_policy import validate_artifact_url


def test_rejects_file_scheme():
    with pytest.raises(DistributionError) as exc:
        validate_artifact_url("file:///etc/passwd", source=ArtifactSourceType.PUBLIC)
    assert exc.value.code == DistributionErrorCode.ARTIFACT_URL_INVALID


def test_rejects_metadata_ip_for_public():
    with pytest.raises(DistributionError) as exc:
        validate_artifact_url("https://169.254.169.254/latest/meta-data/", source=ArtifactSourceType.PUBLIC)
    assert exc.value.code == DistributionErrorCode.ARTIFACT_SSRF_BLOCKED


def test_allows_localhost_http_in_test_mode():
    validate_artifact_url(
        "http://127.0.0.1:8765/artifacts/pkg.emicpkg",
        source=ArtifactSourceType.PUBLIC,
        require_https=False,
    )


def test_blocks_private_ip_for_public():
    with pytest.raises(DistributionError) as exc:
        validate_artifact_url("https://192.168.1.10/pkg.emicpkg", source=ArtifactSourceType.PUBLIC, require_https=True)
    assert exc.value.code == DistributionErrorCode.ARTIFACT_SSRF_BLOCKED
