"""075 — Heartbeat account API call audit timestamps."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "075_heartbeat_account_api_audit"
down_revision = "074_heartbeat_gridx_provider"
branch_labels = None
depends_on = None


def _column_names(table: str) -> set[str]:
    return {c["name"] for c in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    cols = _column_names("heartbeat_accounts")
    additions = [
        ("last_api_call_at", sa.DateTime(timezone=True), None),
        ("last_successful_api_call_at", sa.DateTime(timezone=True), None),
    ]
    missing = [(name, col_type) for name, col_type, _ in additions if name not in cols]
    if missing:
        with op.batch_alter_table("heartbeat_accounts") as batch:
            for name, col_type in missing:
                batch.add_column(sa.Column(name, col_type, nullable=True))


def downgrade() -> None:
    cols = _column_names("heartbeat_accounts")
    for name in ("last_successful_api_call_at", "last_api_call_at"):
        if name in cols:
            with op.batch_alter_table("heartbeat_accounts") as batch:
                batch.drop_column(name)
