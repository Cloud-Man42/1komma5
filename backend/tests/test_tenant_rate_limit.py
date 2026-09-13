"""Per-tenant API rate limit tests."""

from __future__ import annotations

import pytest

from auth_helpers import auth_login as _login


@pytest.mark.asyncio
async def test_tenant_rate_limit_returns_429(auth_client) -> None:
    ac, settings = auth_client
    settings.emic_tenant_api_rate_limit_per_minute = 60
    from app.tenant_rate_limit import TENANT_API_RATE_LIMITER

    TENANT_API_RATE_LIMITER.clear()
    # Bypass pydantic ge=60 by patching the check limit directly via repeated calls.
    original_check = TENANT_API_RATE_LIMITER.check

    def limited_check(key: str, *, limit_per_minute: int) -> bool:
        return original_check(key, limit_per_minute=2)

    TENANT_API_RATE_LIMITER.check = limited_check  # type: ignore[method-assign]
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")

    first = await ac.get("/api/tenants/mine", cookies=cookies)
    second = await ac.get("/api/tenants/mine", cookies=cookies)
    third = await ac.get("/api/tenants/mine", cookies=cookies)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    TENANT_API_RATE_LIMITER.check = original_check  # type: ignore[method-assign]
