"""Add manual override expiry to EV chargers."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_ev_charger_override"
down_revision: Union[str, None] = "007_dashboard_refresh_seconds"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ev_chargers",
        sa.Column("override_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ev_chargers", "override_until")
