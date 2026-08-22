"""Add generic EV charger integration framework fields."""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision: str = "024_ev_charger_framework"
down_revision: str | None = "023_arctic_spa_consumers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ev_chargers", sa.Column("manufacturer_id", sa.String(length=64), nullable=True))
    op.add_column("ev_chargers", sa.Column("model_id", sa.String(length=64), nullable=True))
    op.add_column("ev_chargers", sa.Column("integration_method", sa.String(length=64), nullable=True))
    op.add_column("ev_chargers", sa.Column("external_charger_id", sa.String(length=128), nullable=True))
    op.add_column("ev_chargers", sa.Column("connection_settings", sa.Text(), nullable=True))
    op.add_column(
        "ev_chargers",
        sa.Column("connection_status", sa.String(length=32), nullable=False, server_default="NOT_CONFIGURED"),
    )
    op.add_column("ev_chargers", sa.Column("last_connection_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ev_chargers", sa.Column("last_connection_test_at", sa.DateTime(timezone=True), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, manufacturer, model, control_source, chargeamp_charger_id, chargeamps_api_key "
            "FROM ev_chargers"
        )
    ).fetchall()
    for row in rows:
        manufacturer_id = _manufacturer_id(row.manufacturer)
        model_id = _model_id(row.model)
        integration_method = "CHARGE_AMPS_CLOUD" if row.control_source == "chargeamp" else row.control_source
        settings = {}
        if row.chargeamp_charger_id:
            settings["charger_id"] = row.chargeamp_charger_id
        connection_status = "CONNECTED" if row.chargeamp_charger_id else "NOT_CONFIGURED"
        bind.execute(
            sa.text(
                "UPDATE ev_chargers SET "
                "manufacturer_id = :manufacturer_id, "
                "model_id = :model_id, "
                "integration_method = :integration_method, "
                "external_charger_id = :external_charger_id, "
                "connection_settings = :connection_settings, "
                "connection_status = :connection_status "
                "WHERE id = :id"
            ),
            {
                "id": row.id,
                "manufacturer_id": manufacturer_id,
                "model_id": model_id,
                "integration_method": integration_method,
                "external_charger_id": row.chargeamp_charger_id,
                "connection_settings": json.dumps(settings) if settings else None,
                "connection_status": connection_status,
            },
        )


def downgrade() -> None:
    op.drop_column("ev_chargers", "last_connection_test_at")
    op.drop_column("ev_chargers", "last_connection_at")
    op.drop_column("ev_chargers", "connection_status")
    op.drop_column("ev_chargers", "connection_settings")
    op.drop_column("ev_chargers", "external_charger_id")
    op.drop_column("ev_chargers", "integration_method")
    op.drop_column("ev_chargers", "model_id")
    op.drop_column("ev_chargers", "manufacturer_id")


def _manufacturer_id(name: str | None) -> str:
    normalized = (name or "charge-amps").strip().lower().replace(" ", "-")
    if normalized in {"chargeamps", "charge-amps"}:
        return "charge-amps"
    return normalized or "unknown"


def _model_id(name: str | None) -> str:
    return (name or "halo").strip().lower().replace(" ", "-") or "unknown"
