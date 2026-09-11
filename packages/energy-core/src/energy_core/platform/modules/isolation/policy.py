"""Runtime isolation policy helpers."""

from __future__ import annotations

from energy_core.platform.modules.governance.types import PublisherTier
from energy_core.platform.modules.packages.types import PackageSource
from energy_core.platform.modules.registry import ModuleDescriptor


def requires_isolated_runtime(
    descriptor: ModuleDescriptor,
    *,
    publisher_tier: str | None,
) -> bool:
    # All installed .emicpkg modules run isolated regardless of publisher tier.
    if descriptor.package_source != PackageSource.BUILT_IN:
        return True
    return False


def tier_allows_runtime(publisher_tier: str | None) -> bool:
    tier = (publisher_tier or PublisherTier.COMMUNITY.value).upper()
    return tier in {PublisherTier.VERIFIED.value, PublisherTier.ORG_APPROVED.value, PublisherTier.OFFICIAL.value}


def runtime_blocked_reason(settings) -> str | None:
    if not settings.runtime_spawn_allowed():
        return "THIRD_PARTY_RUNTIME_DISABLED"
    return None
