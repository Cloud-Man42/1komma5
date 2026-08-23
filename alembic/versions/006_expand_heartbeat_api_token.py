"""Expand HeartBeat api_token column for JWT storage."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_expand_heartbeat_api_token"
down_revision: Union[str, None] = "005_ev_bridge_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Batch mode so SQLite, which cannot ALTER COLUMN, rebuilds the table instead.
    with op.batch_alter_table("heartbeat_settings") as batch:
        batch.alter_column(
            "api_token",
            existing_type=sa.String(length=1024),
            type_=sa.Text(),
            existing_nullable=False,
            existing_server_default="",
        )


def downgrade() -> None:
    with op.batch_alter_table("heartbeat_settings") as batch:
        batch.alter_column(
            "api_token",
            existing_type=sa.Text(),
            type_=sa.String(length=1024),
            existing_nullable=False,
            existing_server_default="",
        )
