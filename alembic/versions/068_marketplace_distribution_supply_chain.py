"""068 — marketplace distribution and supply-chain (Step 5C.3 / 5C.4)."""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "068_marketplace_distribution_supply_chain"
down_revision = "067_module_governance"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    return column in {c["name"] for c in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())

    if "marketplace_artifacts" not in tables:
        op.create_table(
            "marketplace_artifacts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("module_id", sa.String(length=128), nullable=False),
            sa.Column("publisher_id", sa.String(length=128), nullable=False),
            sa.Column("version", sa.String(length=64), nullable=False),
            sa.Column("release_id", sa.String(length=256), nullable=False),
            sa.Column("content_sha256", sa.String(length=128), nullable=False, unique=True),
            sa.Column("artifact_size", sa.Integer(), nullable=True),
            sa.Column("source_type", sa.String(length=32), nullable=False, server_default="PUBLIC"),
            sa.Column("state", sa.String(length=32), nullable=False, server_default="DISCOVERED"),
            sa.Column("cache_path", sa.Text(), nullable=True),
            sa.Column("quarantine_path", sa.Text(), nullable=True),
            sa.Column("provenance_json", sa.Text(), nullable=True),
            sa.Column("reason_codes_json", sa.Text(), nullable=True),
            sa.Column("catalog_version", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("module_id", "version", "content_sha256", name="uq_marketplace_artifact_release_digest"),
        )
        op.create_index("ix_marketplace_artifacts_module_version", "marketplace_artifacts", ["module_id", "version"])
        op.create_index("ix_marketplace_artifacts_state", "marketplace_artifacts", ["state"])

    if "marketplace_artifact_security" not in tables:
        op.create_table(
            "marketplace_artifact_security",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("artifact_id", sa.Integer(), nullable=False, unique=True),
            sa.Column("integrity_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("integrity_verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("sbom_status", sa.String(length=32), nullable=False, server_default="MISSING"),
            sa.Column("advisory_status", sa.String(length=32), nullable=False, server_default="UNAVAILABLE"),
            sa.Column("highest_severity", sa.String(length=32), nullable=False, server_default="UNKNOWN"),
            sa.Column("vulnerability_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("critical_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("high_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("security_review_required", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("policy_decision", sa.String(length=64), nullable=True),
            sa.Column("reason_codes_json", sa.Text(), nullable=True),
            sa.Column("risk_evaluated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("snapshot_json", sa.Text(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    if "marketplace_sboms" not in tables:
        op.create_table(
            "marketplace_sboms",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("artifact_id", sa.Integer(), nullable=False, unique=True),
            sa.Column("module_id", sa.String(length=128), nullable=False),
            sa.Column("version", sa.String(length=64), nullable=False),
            sa.Column("artifact_digest", sa.String(length=128), nullable=False),
            sa.Column("sbom_digest", sa.String(length=128), nullable=False),
            sa.Column("format", sa.String(length=32), nullable=False, server_default="CycloneDX"),
            sa.Column("spec_version", sa.String(length=32), nullable=True),
            sa.Column("raw_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_marketplace_sboms_digest", "marketplace_sboms", ["sbom_digest"])

    if "marketplace_sbom_components" not in tables:
        op.create_table(
            "marketplace_sbom_components",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("sbom_id", sa.Integer(), nullable=False),
            sa.Column("component_name", sa.String(length=256), nullable=False),
            sa.Column("component_version", sa.String(length=128), nullable=True),
            sa.Column("purl", sa.String(length=512), nullable=True),
            sa.Column("cpe", sa.String(length=512), nullable=True),
            sa.Column("supplier", sa.String(length=256), nullable=True),
            sa.Column("licenses_json", sa.Text(), nullable=True),
        )
        op.create_index("ix_marketplace_sbom_components_purl", "marketplace_sbom_components", ["purl"])

    if "marketplace_advisories" not in tables:
        op.create_table(
            "marketplace_advisories",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("advisory_id", sa.String(length=128), nullable=False, unique=True),
            sa.Column("source", sa.String(length=64), nullable=False, server_default="emic"),
            sa.Column("severity", sa.String(length=32), nullable=False),
            sa.Column("published_at", sa.String(length=64), nullable=True),
            sa.Column("updated_at", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
            sa.Column("withdrawn", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("references_json", sa.Text(), nullable=True),
            sa.Column("generation", sa.Integer(), nullable=False, server_default="1"),
        )
        op.create_index("ix_marketplace_advisories_severity", "marketplace_advisories", ["severity"])

    if "marketplace_advisory_affected" not in tables:
        op.create_table(
            "marketplace_advisory_affected",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("advisory_id", sa.String(length=128), nullable=False),
            sa.Column("affected_purl", sa.String(length=512), nullable=True),
            sa.Column("affected_package", sa.String(length=256), nullable=True),
            sa.Column("version_range", sa.String(length=256), nullable=True),
            sa.Column("fixed_versions_json", sa.Text(), nullable=True),
        )
        op.create_index("ix_marketplace_advisory_affected_purl", "marketplace_advisory_affected", ["affected_purl"])

    if "marketplace_release_vulnerabilities" not in tables:
        op.create_table(
            "marketplace_release_vulnerabilities",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("artifact_id", sa.Integer(), nullable=False),
            sa.Column("advisory_id", sa.String(length=128), nullable=False),
            sa.Column("component_name", sa.String(length=256), nullable=False),
            sa.Column("component_version", sa.String(length=128), nullable=True),
            sa.Column("purl", sa.String(length=512), nullable=True),
            sa.Column("severity", sa.String(length=32), nullable=False),
            sa.Column("matched", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("version_status", sa.String(length=32), nullable=False, server_default="UNKNOWN"),
        )
        op.create_index("ix_marketplace_release_vuln_artifact", "marketplace_release_vulnerabilities", ["artifact_id"])
        op.create_index("ix_marketplace_release_vuln_advisory", "marketplace_release_vulnerabilities", ["advisory_id"])

    if "marketplace_trust_cache" in tables:
        if not _has_column("marketplace_trust_cache", "advisories_json"):
            op.add_column("marketplace_trust_cache", sa.Column("advisories_json", sa.Text(), nullable=True))
        if not _has_column("marketplace_trust_cache", "advisories_generation"):
            op.add_column("marketplace_trust_cache", sa.Column("advisories_generation", sa.Integer(), nullable=True))
        if not _has_column("marketplace_trust_cache", "advisories_content_hash"):
            op.add_column("marketplace_trust_cache", sa.Column("advisories_content_hash", sa.String(length=128), nullable=True))
        if not _has_column("marketplace_trust_cache", "advisories_updated_at"):
            op.add_column(
                "marketplace_trust_cache", sa.Column("advisories_updated_at", sa.DateTime(timezone=True), nullable=True)
            )

    if "module_installation_policy" in tables:
        if not _has_column("module_installation_policy", "supply_chain_policy_json"):
            op.add_column(
                "module_installation_policy",
                sa.Column("supply_chain_policy_json", sa.Text(), nullable=False, server_default="{}"),
            )
            default_sc = json.dumps(
                {
                    "require_sbom": False,
                    "deny_critical_vulnerabilities": True,
                    "max_allowed_severity": "HIGH",
                    "require_review_for_high": True,
                }
            )
            op.execute(
                sa.text(
                    "UPDATE module_installation_policy SET supply_chain_policy_json = :sc "
                    "WHERE supply_chain_policy_json IS NULL OR supply_chain_policy_json = '{}'"
                ).bindparams(sc=default_sc)
            )


def downgrade() -> None:
    if _has_column("module_installation_policy", "supply_chain_policy_json"):
        op.drop_column("module_installation_policy", "supply_chain_policy_json")
    for col in ("advisories_updated_at", "advisories_content_hash", "advisories_generation", "advisories_json"):
        if _has_column("marketplace_trust_cache", col):
            op.drop_column("marketplace_trust_cache", col)
    op.drop_index("ix_marketplace_release_vuln_advisory", table_name="marketplace_release_vulnerabilities")
    op.drop_index("ix_marketplace_release_vuln_artifact", table_name="marketplace_release_vulnerabilities")
    op.drop_table("marketplace_release_vulnerabilities")
    op.drop_index("ix_marketplace_advisory_affected_purl", table_name="marketplace_advisory_affected")
    op.drop_table("marketplace_advisory_affected")
    op.drop_index("ix_marketplace_advisories_severity", table_name="marketplace_advisories")
    op.drop_table("marketplace_advisories")
    op.drop_index("ix_marketplace_sbom_components_purl", table_name="marketplace_sbom_components")
    op.drop_table("marketplace_sbom_components")
    op.drop_index("ix_marketplace_sboms_digest", table_name="marketplace_sboms")
    op.drop_table("marketplace_sboms")
    op.drop_table("marketplace_artifact_security")
    op.drop_index("ix_marketplace_artifacts_state", table_name="marketplace_artifacts")
    op.drop_index("ix_marketplace_artifacts_module_version", table_name="marketplace_artifacts")
    op.drop_table("marketplace_artifacts")
