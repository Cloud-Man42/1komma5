"""Ensure all /api routes require admin auth except explicit allowlist."""

from __future__ import annotations

import re

import pytest
from app.deps import set_session_factory
from app.main import create_app
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.session import create_engine, create_session_factory
from energy_core.seed import seed_sites
from httpx import ASGITransport, AsyncClient
from starlette.routing import Route


ALLOWLIST_PREFIXES = (
    "/api/v1/display",
    "/api/v1/widget",
)

ALLOWLIST_EXACT = frozenset({"/health"})


def _route_template(route: Route) -> str:
    path = route.path
    for name in route.param_convertors:
        path = re.sub(r"\{[^}]+\}", "test", path, count=1)
    return path


def _is_allowlisted(path: str) -> bool:
    if path in ALLOWLIST_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in ALLOWLIST_PREFIXES)


def _collect_api_routes(app) -> list[tuple[str, str]]:
    routes: list[tuple[str, str]] = []
    for route in app.routes:
        if not isinstance(route, Route):
            continue
        if not route.path.startswith("/api"):
            continue
        if _is_allowlisted(route.path):
            continue
        methods = sorted(method for method in route.methods if method not in {"HEAD", "OPTIONS"})
        for method in methods:
            routes.append((method, _route_template(route)))
    return routes


@pytest.fixture
async def secured_app_client(tmp_path):
    db_file = tmp_path / "route-auth-coverage.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_ADMIN_TOKEN="admin-secret",
        emic_user_auth_enabled=True,
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_sites(session)
        from energy_core.auth.seed_rbac import ensure_rbac_seed

        await ensure_rbac_seed(session)
        await session.commit()

    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, app
    await engine.dispose()


@pytest.mark.asyncio
async def test_all_api_routes_reject_anonymous_access(secured_app_client) -> None:
    ac, app = secured_app_client
    failures: list[str] = []

    for method, path in _collect_api_routes(app):
        response = await ac.request(method, path)
        if response.status_code not in {401, 403, 404, 405, 422}:
            failures.append(f"{method} {path} -> {response.status_code}")

    assert not failures, "Routes without admin auth:\n" + "\n".join(failures)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("GET", "/api/sites", None),
        ("GET", "/api/sites/akarp/vehicles", None),
        ("PATCH", "/api/sites/akarp/heartbeat/bridge/settings", {"simulation_mode": True}),
        (
            "PUT",
            "/api/sites/akarp/historical-energy/2025",
            {
                "source": "coverage-test",
                "estimated": True,
                "months": [{"month": m, "imported_kwh": 1.0} for m in range(1, 13)],
            },
        ),
    ],
)
async def test_protected_routes_accept_valid_admin_token(
    secured_app_client,
    method: str,
    path: str,
    json_body: dict | None,
) -> None:
    ac, _ = secured_app_client
    headers = {"Authorization": "Bearer admin-secret"}
    response = await ac.request(method, path, json=json_body, headers=headers)
    assert response.status_code not in {401, 403}, response.text
