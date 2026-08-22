"""Add dashboard refresh interval to heartbeat settings."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_dashboard_refresh_seconds"
down_revision: Union[str, None] = "006_expand_heartbeat_api_token"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "heartbeat_settings",
        sa.Column("dashboard_refresh_seconds", sa.Integer(), nullable=False, server_default="30"),
    )


def downgrade() -> None:
    op.drop_column("heartbeat_settings", "dashboard_refresh_seconds")
