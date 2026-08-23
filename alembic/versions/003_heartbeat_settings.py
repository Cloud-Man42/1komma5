"""Add editable HeartBeat settings table."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003_heartbeat_settings"
down_revision: str | None = "002_timescaledb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "heartbeat_settings",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("connection_type", sa.String(length=16), nullable=False, server_default="mock"),
        sa.Column("host", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("port", sa.Integer(), nullable=False, server_default="443"),
        sa.Column("use_tls", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("api_path", sa.String(length=128), nullable=False, server_default="/api"),
        sa.Column("poll_interval_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("username", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("password", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("api_token", sa.String(length=1024), nullable=False, server_default=""),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        INSERT INTO heartbeat_settings (id, connection_type, host, port, use_tls, api_path, poll_interval_seconds)
        VALUES (1, 'mock', '', 443, true, '/api', 60)
        """
    )


def downgrade() -> None:
    op.drop_table("heartbeat_settings")
