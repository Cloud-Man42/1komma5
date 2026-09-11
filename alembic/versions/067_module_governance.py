"""067 — module governance (Step 5C.2)."""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "067_module_governance"
down_revision = "066_marketplace_trust_cache_hardening"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _column_names(table: str) -> set[str]:
    return {col["name"] for col in inspect(op.get_bind()).get_columns(table)}


def _seed_governance_data() -> None:
    default_policy = {
        "allowed_tiers": ["OFFICIAL", "VERIFIED", "ORG_APPROVED"],
        "publisher_allowlist": [],
        "publisher_denylist": [],
        "module_allowlist": [],
        "module_denylist": [],
        "blocked_permissions": [],
        "control_module_policy": "VERIFIED_OK",
        "break_glass_enabled": False,
    }
    op.execute(
        sa.text(
            "INSERT INTO module_installation_policy "
            "(policy_scope, policy_version, allowed_tiers_json, publisher_allowlist_json, "
            "publisher_denylist_json, module_allowlist_json, module_denylist_json, "
            "blocked_permissions_json, control_module_policy, break_glass_enabled) "
            "SELECT :scope, 1, :allowed, '[]', '[]', '[]', '[]', '[]', 'VERIFIED_OK', :break_glass "
            "WHERE NOT EXISTS (SELECT 1 FROM module_installation_policy WHERE policy_scope = :scope)"
        ).bindparams(
            scope="installation",
            allowed=json.dumps(default_policy["allowed_tiers"]),
            break_glass=False,
        )
    )

    conn = op.get_bind()
    emic = conn.execute(sa.text("SELECT publisher_id FROM module_publishers WHERE publisher_id = 'emic'")).fetchone()
    if emic is None:
        conn.execute(
            sa.text(
                "INSERT INTO module_publishers (publisher_id, display_name, tier, status) "
                "VALUES ('emic', 'EMIC Official', 'OFFICIAL', 'ACTIVE')"
            )
        )
    if "module_publisher_keys" in _table_names():
        rows = conn.execute(sa.text("SELECT DISTINCT publisher_id FROM module_publisher_keys")).fetchall()
        for (publisher_id,) in rows:
            if publisher_id == "emic":
                continue
            exists = conn.execute(
                sa.text("SELECT publisher_id FROM module_publishers WHERE publisher_id = :pid"),
                {"pid": publisher_id},
            ).fetchone()
            if exists is None:
                conn.execute(
                    sa.text(
                        "INSERT INTO module_publishers (publisher_id, display_name, tier, status) "
                        "VALUES (:pid, :name, 'ORG_APPROVED', 'ACTIVE')"
                    ),
                    {"pid": publisher_id, "name": publisher_id},
                )


def upgrade() -> None:
    tables = _table_names()

    if "module_publishers" not in tables:
        op.create_table(
            "module_publishers",
            sa.Column("publisher_id", sa.String(length=128), primary_key=True),
            sa.Column("display_name", sa.String(length=256), nullable=False),
            sa.Column("legal_name", sa.String(length=256), nullable=True),
            sa.Column("organization", sa.String(length=256), nullable=True),
            sa.Column("verified_domain", sa.String(length=256), nullable=True),
            sa.Column("tier", sa.String(length=32), nullable=False, server_default="ORG_APPROVED"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
        )
    if "module_publisher_verifications" not in tables:
        op.create_table(
            "module_publisher_verifications",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("publisher_id", sa.String(length=128), nullable=False),
            sa.Column("verification_type", sa.String(length=64), nullable=False, server_default="manual"),
            sa.Column("verified_domain", sa.String(length=256), nullable=True),
            sa.Column("verified_organization", sa.String(length=256), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
            sa.Column("verified_by", sa.String(length=128), nullable=True),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index(
            "ix_module_publisher_verifications_publisher_id",
            "module_publisher_verifications",
            ["publisher_id"],
        )
    if "module_ownership" not in tables:
        op.create_table(
            "module_ownership",
            sa.Column("module_id", sa.String(length=128), primary_key=True),
            sa.Column("publisher_id", sa.String(length=128), nullable=False),
            sa.Column("protected", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_module_ownership_publisher_id", "module_ownership", ["publisher_id"])
    if "module_ownership_transfers" not in tables:
        op.create_table(
            "module_ownership_transfers",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("module_id", sa.String(length=128), nullable=False),
            sa.Column("from_publisher_id", sa.String(length=128), nullable=False),
            sa.Column("to_publisher_id", sa.String(length=128), nullable=False),
            sa.Column("from_tier", sa.String(length=32), nullable=True),
            sa.Column("to_tier", sa.String(length=32), nullable=True),
            sa.Column("requested_by", sa.String(length=128), nullable=False),
            sa.Column("approved_by", sa.String(length=128), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_module_ownership_transfers_module_id", "module_ownership_transfers", ["module_id"])
    if "module_installation_policy" not in tables:
        op.create_table(
            "module_installation_policy",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("policy_scope", sa.String(length=64), nullable=False, unique=True),
            sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("allowed_tiers_json", sa.Text(), nullable=False),
            sa.Column("publisher_allowlist_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("publisher_denylist_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("module_allowlist_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("module_denylist_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("blocked_permissions_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("control_module_policy", sa.String(length=32), nullable=False, server_default="VERIFIED_OK"),
            sa.Column("break_glass_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("updated_by", sa.String(length=128), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if "module_policy_history" not in tables:
        op.create_table(
            "module_policy_history",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("policy_scope", sa.String(length=64), nullable=False),
            sa.Column("policy_version", sa.Integer(), nullable=False),
            sa.Column("snapshot_json", sa.Text(), nullable=False),
            sa.Column("updated_by", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_module_policy_history_policy_scope", "module_policy_history", ["policy_scope"])

    if "module_publisher_keys" in _table_names():
        key_columns = _column_names("module_publisher_keys")
        if "valid_from" not in key_columns:
            op.add_column("module_publisher_keys", sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True))
        if "valid_until" not in key_columns:
            op.add_column("module_publisher_keys", sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True))
        if "revoked_at" not in key_columns:
            op.add_column("module_publisher_keys", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
        if "revocation_reason" not in key_columns:
            op.add_column("module_publisher_keys", sa.Column("revocation_reason", sa.Text(), nullable=True))

    _seed_governance_data()


def downgrade() -> None:
    op.drop_column("module_publisher_keys", "revocation_reason")
    op.drop_column("module_publisher_keys", "revoked_at")
    op.drop_column("module_publisher_keys", "valid_until")
    op.drop_column("module_publisher_keys", "valid_from")
    op.drop_index("ix_module_policy_history_policy_scope", table_name="module_policy_history")
    op.drop_table("module_policy_history")
    op.drop_table("module_installation_policy")
    op.drop_index("ix_module_ownership_transfers_module_id", table_name="module_ownership_transfers")
    op.drop_table("module_ownership_transfers")
    op.drop_index("ix_module_ownership_publisher_id", table_name="module_ownership")
    op.drop_table("module_ownership")
    op.drop_index("ix_module_publisher_verifications_publisher_id", table_name="module_publisher_verifications")
    op.drop_table("module_publisher_verifications")
    op.drop_table("module_publishers")
