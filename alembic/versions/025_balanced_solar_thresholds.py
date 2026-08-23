"""Lower solar export thresholds so solar charging engages in everyday conditions."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "025_balanced_solar_thresholds"
down_revision: str | None = "024_ev_charger_framework"
branch_labels = None
depends_on = None

# Only migrate chargers still on the previous defaults so manual tuning is preserved.
_OLD_START_W = 1500.0
_OLD_STOP_W = 800.0
_OLD_START_DELAY_S = 30

_NEW_START_W = 1000.0
_NEW_STOP_W = 600.0
_NEW_START_DELAY_S = 15


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE ev_chargers SET solar_start_threshold_w = :new_start "
            "WHERE solar_start_threshold_w = :old_start"
        ),
        {"new_start": _NEW_START_W, "old_start": _OLD_START_W},
    )
    bind.execute(
        sa.text(
            "UPDATE ev_chargers SET solar_stop_threshold_w = :new_stop "
            "WHERE solar_stop_threshold_w = :old_stop"
        ),
        {"new_stop": _NEW_STOP_W, "old_stop": _OLD_STOP_W},
    )
    bind.execute(
        sa.text(
            "UPDATE ev_chargers SET solar_start_delay_seconds = :new_delay "
            "WHERE solar_start_delay_seconds = :old_delay"
        ),
        {"new_delay": _NEW_START_DELAY_S, "old_delay": _OLD_START_DELAY_S},
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE ev_chargers SET solar_start_threshold_w = :old_start "
            "WHERE solar_start_threshold_w = :new_start"
        ),
        {"new_start": _NEW_START_W, "old_start": _OLD_START_W},
    )
    bind.execute(
        sa.text(
            "UPDATE ev_chargers SET solar_stop_threshold_w = :old_stop "
            "WHERE solar_stop_threshold_w = :new_stop"
        ),
        {"new_stop": _NEW_STOP_W, "old_stop": _OLD_STOP_W},
    )
    bind.execute(
        sa.text(
            "UPDATE ev_chargers SET solar_start_delay_seconds = :old_delay "
            "WHERE solar_start_delay_seconds = :new_delay"
        ),
        {"new_delay": _NEW_START_DELAY_S, "old_delay": _OLD_START_DELAY_S},
    )
