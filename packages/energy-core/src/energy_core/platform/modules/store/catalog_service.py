"""Unified Module Store catalog aggregation service."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import IntEnum
from typing import Any

from packaging.version import InvalidVersion, Version
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import AppEnvironment, Settings
from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.db.models import SiteModel
from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.distribution.artifact_repository import ArtifactRepository
from energy_core.platform.modules.distribution.catalog_resolver import CatalogReleaseResolver
from energy_core.platform.modules.distribution.types import ArtifactSourceType, ArtifactState
from energy_core.platform.modules.governance.evaluation_service import GovernanceEvaluationService
from energy_core.platform.modules.governance.policy_engine import ModuleInstallPolicyEngine
from energy_core.platform.modules.governance.publisher_repository import PublisherRepository
from energy_core.platform.modules.governance.risk_classifier import is_control_capable
from energy_core.platform.modules.governance.types import PolicyAction, PolicyDecision, PublisherStatus, PublisherTier
from energy_core.platform.modules.marketplace.trust_cache import MarketplaceTrustCacheRepository
from energy_core.platform.modules.marketplace.types import MetadataHealth
from energy_core.platform.modules.packages.catalog import CatalogEntry, list_catalog_entries
from energy_core.platform.modules.packages.paths import is_protected_module_id
from energy_core.platform.modules.packages.store_service import PackageStoreService
from energy_core.platform.modules.packages.types import PackageSource, PackageState
from energy_core.platform.modules.registry import ModuleDescriptor, default_module_registry
from energy_core.platform.modules.store.capability_labels import capability_label, permission_view
from energy_core.platform.modules.store.categories import STORE_CATEGORIES, categories_for_module, normalize_category
from energy_core.platform.modules.store.store_content import sanitize_text, sanitize_url
from energy_core.platform.modules.store.store_reason_codes import explain_reason_codes
from energy_core.platform.modules.store.types import (
    StoreCapabilityView,
    StoreCatalogPage,
    StoreCompatibilityView,
    StoreFeatureView,
    StoreInstallState,
    StoreModuleDetail,
    StoreModuleSummary,
    StoreOrigin,
    StorePermissionView,
    StorePolicyView,
    StorePreflightResponse,
    StorePrimaryAction,
    StorePublisherDetail,
    StorePublisherSummary,
    StoreReleaseItem,
    StoreSecurityBadge,
    StoreSecurityCenterView,
    StoreSecurityView,
    StoreSiteOption,
    StoreStatusView,
)


class _SourceRank(IntEnum):
    LOCAL = 0
    INTERNAL = 1
    ORG = 2
    BUILT_IN = 3
    INSTALLED = 4
    PUBLIC = 5


@dataclass
class _Candidate:
    module_id: str
    display_name: str
    description: str
    publisher_id: str
    version: str
    origin: str
    source_rank: _SourceRank
    device_categories: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    features: tuple[dict[str, Any], ...] = ()
    configuration_schema: dict[str, Any] = field(default_factory=dict)
    supports_per_site_activation: bool = True
    minimum_emic_version: str | None = None
    maximum_emic_version: str | None = None
    module_api_version: int | None = None
    dependencies: tuple[dict[str, str], ...] = ()
    published_at: str | None = None
    icon_url: str | None = None
    catalog_entry_id: str | None = None
    marketplace_release: dict[str, Any] | None = None


_ALLOWED_SORTS = frozenset({"recommended", "name", "recently_updated", "installed", "security_status"})


class StoreCatalogService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._installed = InstalledPackageRepository(session)
        self._publishers = PublisherRepository(session)
        self._governance = GovernanceEvaluationService(session)
        self._package_store = PackageStoreService(session, settings)
        self._artifact_repo = ArtifactRepository(session)

    async def build_status(self) -> StoreStatusView:
        repo = MarketplaceTrustCacheRepository(self._session)
        view = await repo.build_status_view(enabled=self._settings.marketplace_metadata_enabled)
        stale = False
        invalid = view.metadata_health == MetadataHealth.INVALID
        if view.catalog_age_seconds is not None and view.catalog_age_seconds > 86400:
            stale = True
        message = "Marketplace healthy"
        if not self._settings.marketplace_metadata_enabled:
            message = "Marketplace metadata disabled — showing local and built-in modules only"
        elif view.offline:
            message = "Marketplace offline — showing cached catalog where available"
        elif invalid:
            message = "Marketplace trust data invalid. Remote installs unavailable."
        elif stale:
            message = "Marketplace information may be outdated."
        return StoreStatusView(
            marketplace_enabled=self._settings.marketplace_metadata_enabled,
            metadata_health=view.metadata_health.value,
            revocation_freshness=view.revocation_freshness.value,
            last_sync=view.last_sync.isoformat() if view.last_sync else None,
            last_success=view.last_success.isoformat() if view.last_success else None,
            last_error=view.last_error,
            offline=view.offline,
            stale=stale,
            invalid=invalid,
            catalog_freshness_seconds=view.catalog_age_seconds,
            message=message,
        )

    async def list_catalog(
        self,
        *,
        search: str | None = None,
        category: str | None = None,
        trust: str | None = None,
        security: str | None = None,
        installed: bool | None = None,
        update_available: bool | None = None,
        compatible: bool | None = None,
        control_capable: bool | None = None,
        official_only: bool | None = None,
        page: int = 1,
        page_size: int = 24,
        sort: str = "recommended",
    ) -> StoreCatalogPage:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        if sort not in _ALLOWED_SORTS:
            sort = "recommended"
        candidates = await self._collect_candidates()
        publisher_map = await self._publisher_map()
        installed_map = {r.module_id: r for r in await self._installed.list_all()}
        summaries: list[StoreModuleSummary] = []
        for cand in candidates.values():
            summary = await self._to_summary(cand, publisher_map, installed_map.get(cand.module_id))
            summaries.append(summary)
        summaries = self._apply_filters(
            summaries,
            search=search,
            category=category,
            trust=trust,
            security=security,
            installed=installed,
            update_available=update_available,
            compatible=compatible,
            control_capable=control_capable,
            official_only=official_only,
        )
        summaries = self._sort_summaries(summaries, sort)
        total = len(summaries)
        start = (page - 1) * page_size
        page_items = tuple(summaries[start : start + page_size])
        category_counts: dict[str, int] = {}
        for item in summaries:
            category_counts[item.category] = category_counts.get(item.category, 0) + 1
        categories = tuple(
            {"id": cat, "label": cat, "count": category_counts.get(cat, 0)}
            for cat in STORE_CATEGORIES
            if category_counts.get(cat, 0) > 0
        )
        status = await self.build_status()
        return StoreCatalogPage(
            modules=page_items,
            page=page,
            page_size=page_size,
            total=total,
            categories=categories,
            marketplace_status={
                "message": status.message,
                "offline": status.offline,
                "stale": status.stale,
                "invalid": status.invalid,
                "last_success": status.last_success,
            },
        )

    async def get_module_detail(self, module_id: str) -> StoreModuleDetail | None:
        candidates = await self._collect_candidates()
        cand = candidates.get(module_id)
        if cand is None:
            return None
        publisher_map = await self._publisher_map()
        installed = await self._installed.get(module_id)
        summary = await self._to_summary(cand, publisher_map, installed)
        permissions = tuple(
            StorePermissionView(permission=p, label=label, risk_level=risk, group=group)
            for p in cand.permissions
            for label, risk, group in [permission_view(p)]
        )
        capabilities = tuple(
            StoreCapabilityView(capability=c, label=capability_label(c)) for c in cand.capabilities
        )
        features = self._build_features(cand)
        compatibility = self._compatibility(cand)
        security = await self._security_view(cand, summary.policy)
        return StoreModuleDetail(
            summary=summary,
            long_description=sanitize_text(cand.description),
            capabilities=capabilities,
            permissions=permissions,
            features=features,
            compatibility=compatibility,
            security=security,
            dependencies=cand.dependencies,
            configuration_schema=cand.configuration_schema,
            supports_per_site_activation=cand.supports_per_site_activation,
        )

    async def list_releases(self, module_id: str) -> tuple[StoreReleaseItem, ...]:
        candidates = await self._collect_candidates()
        cand = candidates.get(module_id)
        if cand is None:
            return ()
        installed = await self._installed.get(module_id)
        items: list[StoreReleaseItem] = []
        if cand.marketplace_release and cand.origin == StoreOrigin.PUBLIC_MARKETPLACE.value:
            cache_row = await MarketplaceTrustCacheRepository(self._session).get_or_create()
            resolver = CatalogReleaseResolver.from_cache_json(cache_row.catalog_json)
            modules = (json.loads(cache_row.catalog_json or "{}").get("modules") or {}).get(module_id, {})
            releases = modules.get("releases") if isinstance(modules, dict) else {}
            if isinstance(releases, dict):
                for version, rel in releases.items():
                    if not isinstance(rel, dict):
                        continue
                    policy = await self._evaluate_policy(
                        module_id=module_id,
                        publisher_id=cand.publisher_id,
                        permissions=cand.permissions,
                        capabilities=cand.capabilities,
                    )
                    items.append(
                        StoreReleaseItem(
                            version=str(version),
                            release_id=str(rel.get("release_id", f"{module_id}@{version}")),
                            channel=str(rel.get("channel", "stable")),
                            published_at=rel.get("published_at"),
                            compatible=self._compatibility(cand).compatible,
                            security_status=policy.decision,
                            installed=bool(installed and installed.installed_version == version),
                            staged=False,
                            policy_decision=policy.decision,
                            reason_codes=policy.reason_codes,
                        )
                    )
        if not items and cand.version:
            policy = await self._evaluate_policy(
                module_id=module_id,
                publisher_id=cand.publisher_id,
                permissions=cand.permissions,
                capabilities=cand.capabilities,
            )
            items.append(
                StoreReleaseItem(
                    version=cand.version,
                    release_id=f"{module_id}@{cand.version}",
                    channel="stable",
                    published_at=cand.published_at,
                    compatible=self._compatibility(cand).compatible,
                    security_status=policy.decision,
                    installed=bool(installed and installed.installed_version == cand.version),
                    staged=bool(installed and installed.package_state == PackageState.AVAILABLE),
                    policy_decision=policy.decision,
                    reason_codes=policy.reason_codes,
                )
            )
        return tuple(sorted(items, key=lambda r: r.version, reverse=True))

    async def list_publishers(self) -> tuple[StorePublisherSummary, ...]:
        candidates = await self._collect_candidates()
        counts: dict[str, int] = {}
        for cand in candidates.values():
            counts[cand.publisher_id] = counts.get(cand.publisher_id, 0) + 1
        rows = await self._publishers.list_publishers()
        return tuple(
            StorePublisherSummary(
                publisher_id=row.publisher_id,
                display_name=row.display_name,
                tier=row.tier,
                status=row.status,
                module_count=counts.get(row.publisher_id, 0),
            )
            for row in rows
        )

    async def get_publisher(self, publisher_id: str) -> StorePublisherDetail | None:
        row = await self._publishers.get(publisher_id)
        if row is None:
            return None
        candidates = await self._collect_candidates()
        modules = tuple(c.module_id for c in candidates.values() if c.publisher_id == publisher_id)
        releases: list[dict[str, str]] = []
        for cand in candidates.values():
            if cand.publisher_id == publisher_id:
                releases.append({"module_id": cand.module_id, "version": cand.version})
        return StorePublisherDetail(
            publisher_id=row.publisher_id,
            display_name=row.display_name,
            legal_name=row.legal_name,
            organization=row.organization,
            tier=row.tier,
            status=row.status,
            verified_domain=row.verified_domain,
            verified_at=row.verified_at.isoformat() if row.verified_at else None,
            active_keys=(),
            modules=modules,
            recent_releases=tuple(releases[:10]),
            security_status="REVOKED" if row.status == PublisherStatus.REVOKED.value else "ACTIVE",
        )

    async def build_security_center(self) -> StoreSecurityCenterView:
        overview = await self._package_store.build_overview()
        catalog = await self.list_catalog(page_size=500)
        reviews = [m for m in catalog.modules if m.primary_action == StorePrimaryAction.SECURITY_REVIEW_REQUIRED.value]
        critical = [m for m in catalog.modules if m.security_badge == StoreSecurityBadge.CRITICAL_ADVISORY.value]
        quarantined = [
            {
                "module_id": card.module_id,
                "version": card.installed_version,
                "publisher": card.publisher,
                "reason": ", ".join(card.attention_reasons),
            }
            for card in overview.installed
            if card.package_state == PackageState.QUARANTINED.value
        ]
        publishers = await self._publishers.list_publishers()
        revoked = tuple(p.publisher_id for p in publishers if p.status == PublisherStatus.REVOKED.value)
        updates = sum(1 for m in catalog.modules if m.update_available)
        status = await self.build_status()
        return StoreSecurityCenterView(
            installed_count=len(overview.installed),
            updates_available=updates,
            security_reviews_required=len(reviews),
            critical_issues=len(critical),
            quarantined_count=len(quarantined),
            revoked_publishers=revoked,
            quarantined=tuple(quarantined),
            critical_advisories=tuple({"module_id": m.module_id, "version": m.latest_version} for m in critical),
            high_advisories=(),
            review_required_modules=tuple(m.module_id for m in reviews),
            metadata_health=status.metadata_health,
        )

    async def preflight(
        self,
        module_id: str,
        version: str,
        *,
        site_slug: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> StorePreflightResponse | None:
        detail = await self.get_module_detail(module_id)
        if detail is None:
            return None
        if detail.summary.latest_version and version != detail.summary.latest_version:
            releases = await self.list_releases(module_id)
            if not any(r.version == version for r in releases):
                return None
        sites = await self._session.scalars(select(SiteModel))
        site_options = tuple(StoreSiteOption(site_slug=s.slug, site_name=s.name) for s in sites)
        config_errors: list[str] = []
        if site_slug and site_slug not in {s.site_slug for s in site_options}:
            config_errors.append("Invalid site selection")
        install_allowed = detail.summary.primary_action in {
            StorePrimaryAction.INSTALL.value,
            StorePrimaryAction.UPDATE.value,
        }
        stage_allowed = install_allowed or detail.summary.primary_action == StorePrimaryAction.SECURITY_REVIEW_REQUIRED.value
        runtime_blocked = (
            not self._settings.third_party_runtime_enabled
            or detail.summary.control_capable
        )
        runtime_message = ""
        if detail.summary.control_capable and not ModuleInstallPolicyEngine.CONTROL_ISOLATION_GATE_OPEN:
            runtime_message = (
                "Runtime execution unavailable until control-module security gate is approved."
            )
        elif not self._settings.third_party_runtime_enabled and detail.summary.origin != StoreOrigin.BUILT_IN.value:
            runtime_message = "Runtime execution is currently disabled by system policy."
        return StorePreflightResponse(
            module_id=module_id,
            version=version,
            display_name=detail.summary.display_name,
            publisher_id=detail.summary.publisher_id,
            publisher_name=detail.summary.publisher_name,
            trust_tier=detail.summary.trust_tier,
            publisher_status=(await self._publishers.get(detail.summary.publisher_id)).status
            if await self._publishers.get(detail.summary.publisher_id)
            else "UNKNOWN",
            signature_valid=detail.security.signature_status == "valid",
            ownership_verified=detail.security.ownership_verified,
            security=detail.security,
            compatibility=detail.compatibility,
            permissions=detail.permissions,
            capabilities=detail.capabilities,
            features=detail.features,
            sites=site_options,
            configuration_schema=detail.configuration_schema,
            policy=detail.summary.policy,
            primary_action=detail.summary.primary_action,
            install_allowed=install_allowed,
            stage_allowed=stage_allowed,
            runtime_blocked=runtime_blocked,
            runtime_message=runtime_message,
            config_errors=tuple(config_errors),
        )

    async def _collect_candidates(self) -> dict[str, _Candidate]:
        merged: dict[str, _Candidate] = {}

        def merge(cand: _Candidate) -> None:
            if is_protected_module_id(cand.module_id) and cand.source_rank == _SourceRank.PUBLIC:
                return
            existing = merged.get(cand.module_id)
            if existing is None or cand.source_rank < existing.source_rank:
                merged[cand.module_id] = cand

        register_default_modules()
        for desc in default_module_registry.list_modules():
            caps = tuple(str(c.value if hasattr(c, "value") else c) for c in desc.capabilities_provided)
            merge(
                _Candidate(
                    module_id=desc.module_id,
                    display_name=desc.name,
                    description=sanitize_text(desc.description),
                    publisher_id=desc.publisher or "emic",
                    version=desc.installed_version or desc.version,
                    origin=StoreOrigin.BUILT_IN.value,
                    source_rank=_SourceRank.BUILT_IN,
                    device_categories=desc.device_categories,
                    capabilities=caps,
                    configuration_schema=dict(desc.configuration_schema),
                    supports_per_site_activation=desc.supports_per_site_activation,
                    minimum_emic_version=self._settings.emic_version,
                    module_api_version=1,
                )
            )

        for entry in list_catalog_entries(self._settings):
            merge(self._candidate_from_catalog(entry))

        for row in await self._installed.list_all():
            meta = row.metadata or {}
            caps = tuple(str(c) for c in meta.get("provided_capabilities") or [])
            perms = tuple(str(p) for p in meta.get("permissions") or [])
            merge(
                _Candidate(
                    module_id=row.module_id,
                    display_name=str(meta.get("name", row.module_id)),
                    description=sanitize_text(str(meta.get("description", ""))),
                    publisher_id=row.publisher,
                    version=row.installed_version,
                    origin=StoreOrigin.INSTALLED.value,
                    source_rank=_SourceRank.INSTALLED,
                    device_categories=tuple(str(c) for c in meta.get("device_categories") or []),
                    capabilities=caps,
                    permissions=perms,
                    configuration_schema=dict(meta.get("configuration_schema") or {}),
                    minimum_emic_version=meta.get("minimum_emic_version"),
                    module_api_version=row.module_api_version,
                )
            )

        if self._settings.marketplace_metadata_enabled:
            cache_row = await MarketplaceTrustCacheRepository(self._session).get_or_create()
            if cache_row.catalog_json:
                raw = json.loads(cache_row.catalog_json)
                modules = raw.get("modules") or {}
                if isinstance(modules, dict):
                    for module_id, entry in modules.items():
                        if not isinstance(entry, dict):
                            continue
                        latest = entry.get("latest_stable")
                        releases = entry.get("releases") if isinstance(entry.get("releases"), dict) else {}
                        rel = releases.get(latest) if latest and isinstance(releases, dict) else None
                        if not isinstance(rel, dict):
                            continue
                        merge(
                            _Candidate(
                                module_id=str(module_id),
                                display_name=sanitize_text(str(entry.get("display_name", module_id))),
                                description=sanitize_text(str(entry.get("description", ""))),
                                publisher_id=str(rel.get("publisher_id") or entry.get("publisher_id", "")),
                                version=str(latest),
                                origin=StoreOrigin.PUBLIC_MARKETPLACE.value,
                                source_rank=_SourceRank.PUBLIC,
                                device_categories=tuple(str(c) for c in entry.get("device_categories") or []),
                                capabilities=tuple(str(c) for c in entry.get("capabilities") or []),
                                permissions=tuple(str(p) for p in entry.get("permissions") or []),
                                published_at=rel.get("published_at"),
                                marketplace_release=rel,
                            )
                        )
        return merged

    def _candidate_from_catalog(self, entry: CatalogEntry) -> _Candidate:
        return _Candidate(
            module_id=entry.module_id,
            display_name=entry.name,
            description=sanitize_text(entry.description),
            publisher_id=entry.publisher,
            version=entry.version,
            origin=StoreOrigin.INTERNAL_STORE.value,
            source_rank=_SourceRank.INTERNAL,
            catalog_entry_id=entry.entry_id,
        )

    async def _publisher_map(self) -> dict[str, Any]:
        rows = await self._publishers.list_publishers()
        return {row.publisher_id: row for row in rows}

    async def _evaluate_policy(
        self,
        *,
        module_id: str,
        publisher_id: str,
        permissions: tuple[str, ...],
        capabilities: tuple[str, ...],
    ) -> StorePolicyView:
        result = await self._governance.evaluate(
            action=PolicyAction.INSTALL,
            module_id=module_id,
            publisher_id=publisher_id,
            permissions=permissions,
            provided_capabilities=capabilities,
            marketplace_enabled=self._settings.marketplace_metadata_enabled,
            app_env_production=self._settings.app_env == AppEnvironment.PRODUCTION,
        )
        explanation = result.explanation or explain_reason_codes(result.reason_codes)
        return StorePolicyView(
            decision=result.decision.value,
            reason_codes=result.reason_codes,
            explanation=explanation,
            publisher_tier=result.publisher_tier,
            control_capable=result.control_capable,
            policy_version=result.policy_version,
        )

    def _compatibility(self, cand: _Candidate) -> StoreCompatibilityView:
        reasons: list[str] = []
        compatible = True
        try:
            if cand.minimum_emic_version and Version(cand.minimum_emic_version) > Version(self._settings.emic_version):
                compatible = False
                reasons.append("EMIC version too old for this module")
            if cand.maximum_emic_version and Version(cand.maximum_emic_version) < Version(self._settings.emic_version):
                compatible = False
                reasons.append("EMIC version too new for this module")
        except InvalidVersion:
            compatible = False
            reasons.append("Invalid version constraint")
        if cand.module_api_version and cand.module_api_version > self._settings.emic_module_api_version:
            compatible = False
            reasons.append("Module runtime protocol not supported")
        return StoreCompatibilityView(
            compatible=compatible,
            emic_version=self._settings.emic_version,
            minimum_emic_version=cand.minimum_emic_version,
            maximum_emic_version=cand.maximum_emic_version,
            module_api_version=self._settings.emic_module_api_version,
            required_emic_module_api_version=cand.module_api_version,
            reasons=tuple(reasons),
        )

    async def _to_summary(
        self,
        cand: _Candidate,
        publisher_map: dict[str, Any],
        installed: Any | None,
    ) -> StoreModuleSummary:
        pub = publisher_map.get(cand.publisher_id)
        tier = pub.tier if pub else PublisherTier.OFFICIAL.value if cand.origin == StoreOrigin.BUILT_IN.value else PublisherTier.VERIFIED.value
        pub_name = pub.display_name if pub else cand.publisher_id
        pub_status = pub.status if pub else PublisherStatus.ACTIVE.value
        policy = await self._evaluate_policy(
            module_id=cand.module_id,
            publisher_id=cand.publisher_id,
            permissions=cand.permissions,
            capabilities=cand.capabilities,
        )
        control = policy.control_capable or is_control_capable(
            permissions=cand.permissions, provided_capabilities=cand.capabilities
        )
        compatibility = self._compatibility(cand)
        installed_version = installed.installed_version if installed else None
        installed_state = StoreInstallState.NOT_INSTALLED.value
        update_available = False
        if cand.origin == StoreOrigin.BUILT_IN.value or installed:
            installed_state = StoreInstallState.INSTALLED.value
        if installed:
            if installed.package_state == PackageState.QUARANTINED:
                installed_state = StoreInstallState.QUARANTINED.value
            elif installed.package_state == PackageState.UPDATE_AVAILABLE:
                installed_state = StoreInstallState.UPDATE_AVAILABLE.value
                update_available = True
            elif installed.package_state == PackageState.AVAILABLE:
                installed_state = StoreInstallState.STAGED.value
            installed_version = installed.installed_version
            if cand.version and installed.installed_version != cand.version:
                update_available = True
        primary = self._primary_action(
            tier=tier,
            pub_status=pub_status,
            policy=policy,
            compatible=compatibility.compatible,
            installed_state=installed_state,
            update_available=update_available,
            control_capable=control,
            origin=cand.origin,
        )
        security_badge = self._security_badge(tier, pub_status, policy)
        cats = categories_for_module(device_categories=cand.device_categories, module_id=cand.module_id)
        return StoreModuleSummary(
            module_id=cand.module_id,
            display_name=cand.display_name,
            publisher_id=cand.publisher_id,
            publisher_name=pub_name,
            description=sanitize_text(cand.description),
            category=cats[0],
            categories=cats,
            icon_url=sanitize_url(cand.icon_url),
            origin=cand.origin,
            trust_tier=tier,
            trust_badge=tier,
            security_badge=security_badge,
            installed_state=installed_state,
            installed_version=installed_version,
            latest_version=cand.version,
            update_available=update_available,
            compatible=compatibility.compatible,
            control_capable=control,
            primary_action=primary,
            policy=policy,
            capabilities_summary=cand.capabilities[:5],
            published_at=cand.published_at,
            source_precedence=cand.origin,
        )

    def _primary_action(
        self,
        *,
        tier: str,
        pub_status: str,
        policy: StorePolicyView,
        compatible: bool,
        installed_state: str,
        update_available: bool,
        control_capable: bool,
        origin: str,
    ) -> str:
        if tier == PublisherTier.REVOKED.value or pub_status == PublisherStatus.REVOKED.value:
            return StorePrimaryAction.REVOKED.value
        if not compatible:
            return StorePrimaryAction.INCOMPATIBLE.value
        if policy.decision == PolicyDecision.DENY.value:
            if PolicyDecision.REQUIRE_SECURITY_REVIEW.value in policy.reason_codes:
                return StorePrimaryAction.SECURITY_REVIEW_REQUIRED.value
            return StorePrimaryAction.BLOCKED_BY_POLICY.value
        if policy.decision == PolicyDecision.REQUIRE_SECURITY_REVIEW.value:
            return StorePrimaryAction.SECURITY_REVIEW_REQUIRED.value
        if installed_state == StoreInstallState.QUARANTINED.value:
            return StorePrimaryAction.BLOCKED_BY_POLICY.value
        if update_available:
            return StorePrimaryAction.UPDATE.value
        if installed_state in {StoreInstallState.INSTALLED.value, StoreInstallState.UPDATE_AVAILABLE.value}:
            if control_capable and origin != StoreOrigin.BUILT_IN.value:
                return StorePrimaryAction.RUNTIME_NOT_PERMITTED.value
            return StorePrimaryAction.INSTALLED.value
        if installed_state == StoreInstallState.STAGED.value:
            return StorePrimaryAction.STAGED.value
        if policy.decision in {PolicyDecision.ALLOW.value, PolicyDecision.REQUIRE_ADMIN_APPROVAL.value}:
            return StorePrimaryAction.INSTALL.value
        return StorePrimaryAction.BLOCKED_BY_POLICY.value

    def _security_badge(self, tier: str, pub_status: str, policy: StorePolicyView) -> str:
        if tier == PublisherTier.REVOKED.value or pub_status == PublisherStatus.REVOKED.value:
            return StoreSecurityBadge.REVOKED.value
        if "VULNERABILITY_CRITICAL" in policy.reason_codes:
            return StoreSecurityBadge.CRITICAL_ADVISORY.value
        if policy.decision == PolicyDecision.REQUIRE_SECURITY_REVIEW.value:
            return StoreSecurityBadge.SECURITY_REVIEW_REQUIRED.value
        if policy.decision == PolicyDecision.ALLOW.value:
            return StoreSecurityBadge.NO_CRITICAL_ISSUES.value
        return StoreSecurityBadge.UNKNOWN.value

    async def _security_view(self, cand: _Candidate, policy: StorePolicyView) -> StoreSecurityView:
        runtime_blocked = cand.origin != StoreOrigin.BUILT_IN.value and (
            not self._settings.third_party_runtime_enabled or policy.control_capable
        )
        runtime_message = ""
        if policy.control_capable:
            runtime_message = "Runtime execution blocked pending control-module security approval."
        elif not self._settings.third_party_runtime_enabled:
            runtime_message = "Runtime execution disabled by system policy."
        return StoreSecurityView(
            artifact_integrity="SHA-256 verified" if cand.marketplace_release else "Local package",
            signature_status="valid" if cand.origin != StoreOrigin.PUBLIC_MARKETPLACE.value else "pending",
            publisher_trust=policy.publisher_tier or cand.publisher_id,
            ownership_verified=True,
            sbom_status="AVAILABLE" if cand.marketplace_release and cand.marketplace_release.get("sbom_ref") else "UNKNOWN",
            sbom_summary=None,
            advisory_status="CLEAN",
            highest_severity="NONE",
            vulnerability_count=0,
            critical_count=0,
            high_count=0,
            revocation_state="ACTIVE" if policy.decision != PolicyDecision.DENY.value else "BLOCKED",
            security_decision=policy.decision,
            reason_codes=policy.reason_codes,
            last_evaluated=datetime.now(UTC).isoformat(),
            runtime_blocked=runtime_blocked,
            runtime_message=runtime_message,
        )

    def _build_features(self, cand: _Candidate) -> tuple[StoreFeatureView, ...]:
        if cand.features:
            return tuple(
                StoreFeatureView(
                    feature_id=str(f.get("feature_id", "")),
                    feature_name=str(f.get("feature_name", "")),
                    description=sanitize_text(str(f.get("description", ""))),
                    required_capabilities=tuple(str(c) for c in f.get("required_capabilities") or []),
                )
                for f in cand.features
                if f.get("feature_id")
            )
        return tuple(
            StoreFeatureView(
                feature_id=cap,
                feature_name=capability_label(cap),
                description="",
                required_capabilities=(cap,),
            )
            for cap in cand.capabilities[:8]
        )

    def _apply_filters(
        self,
        items: list[StoreModuleSummary],
        *,
        search: str | None,
        category: str | None,
        trust: str | None,
        security: str | None,
        installed: bool | None,
        update_available: bool | None,
        compatible: bool | None,
        control_capable: bool | None,
        official_only: bool | None,
    ) -> list[StoreModuleSummary]:
        result = items
        if search:
            q = search.lower()[:200]
            result = [
                m
                for m in result
                if q in m.display_name.lower()
                or q in m.module_id.lower()
                or q in m.publisher_name.lower()
                or q in m.description.lower()
                or q in m.category.lower()
                or any(q in c.lower() for c in m.capabilities_summary)
            ]
        if category:
            result = [m for m in result if m.category == category or category in m.categories]
        if trust:
            result = [m for m in result if m.trust_tier == trust.upper()]
        if security:
            result = [m for m in result if m.security_badge == security.upper()]
        if installed is True:
            result = [
                m
                for m in result
                if m.installed_state
                in {
                    StoreInstallState.INSTALLED.value,
                    StoreInstallState.UPDATE_AVAILABLE.value,
                    StoreInstallState.STAGED.value,
                    StoreInstallState.QUARANTINED.value,
                }
            ]
        elif installed is False:
            result = [m for m in result if m.installed_state == StoreInstallState.NOT_INSTALLED.value]
        if update_available is True:
            result = [m for m in result if m.update_available]
        elif update_available is False:
            result = [m for m in result if not m.update_available]
        if compatible is True:
            result = [m for m in result if m.compatible]
        elif compatible is False:
            result = [m for m in result if not m.compatible]
        if control_capable is True:
            result = [m for m in result if m.control_capable]
        elif control_capable is False:
            result = [m for m in result if not m.control_capable]
        if official_only:
            result = [m for m in result if m.trust_tier == PublisherTier.OFFICIAL.value]
        return result

    def _sort_summaries(self, items: list[StoreModuleSummary], sort: str) -> list[StoreModuleSummary]:
        if sort == "name":
            return sorted(items, key=lambda m: m.display_name.lower())
        if sort == "recently_updated":
            return sorted(items, key=lambda m: m.published_at or "", reverse=True)
        if sort == "installed":
            return sorted(items, key=lambda m: (0 if m.installed_state != StoreInstallState.NOT_INSTALLED.value else 1, m.display_name))
        if sort == "security_status":
            return sorted(items, key=lambda m: m.security_badge)
        return sorted(
            items,
            key=lambda m: (
                0 if m.trust_tier == PublisherTier.OFFICIAL.value else 1,
                0 if m.origin == StoreOrigin.BUILT_IN.value else 1,
                m.display_name.lower(),
            ),
        )
