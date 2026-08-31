"""Backend startup guards."""

from __future__ import annotations

import pytest

from app.main import create_app, lifespan
from energy_core.config import Settings


@pytest.mark.asyncio
async def test_production_startup_rejects_chargeamps_mock(monkeypatch):
    monkeypatch.setenv("CHARGEAMPS_MOCK", "true")
    settings = Settings(_env_file=None, APP_ENV="production", DATABASE_URL="sqlite+aiosqlite:///:memory:")
    app = create_app(settings)

    with pytest.raises(RuntimeError, match="CHARGEAMPS_MOCK"):
        async with lifespan(app):
            pass
