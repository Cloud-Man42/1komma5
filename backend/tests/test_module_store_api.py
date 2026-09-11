"""Module Store overview and publisher API tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.deps import set_session_factory
from app.main import create_app
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.session import create_engine, create_session_factory
from energy_core.platform.modules.packages.signing import generate_ed25519_keypair
from energy_core.seed import seed_sites
from httpx import ASGITransport, AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "packages" / "energy-core" / "tests" / "fixtures" / "modules"
CATALOG = FIXTURES / "catalog"


def _restore_default_registry() -> None:
    from energy_core.platform.modules.bootstrap import register_default_modules
    from energy_core.platform.modules.registry import default_module_registry

    default_module_registry.clear()
    register_default_modules()


@pytest.fixture
async def store_api_client(tmp_path):
    db_file = tmp_path / "module-store.db"
    modules_path = tmp_path / "modules"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_MODULES_PATH=str(modules_path),
        EMIC_ALLOW_UNSIGNED_MODULES=True,
        EMIC_MODULE_CATALOG_PATH=str(CATALOG),
        EMIC_ADMIN_TOKEN="admin-secret",
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_sites(session)
        await session.commit()
    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, settings, session_factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_store_overview_requires_admin(store_api_client) -> None:
    ac, _, _ = store_api_client
    res = await ac.get("/api/modules/packages/store/overview")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_store_overview_lists_installed_and_catalog(store_api_client) -> None:
    ac, _, _ = store_api_client
    headers = {"Authorization": "Bearer admin-secret"}
    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
    await ac.post(
        "/api/modules/packages/install",
        headers=headers,
        files={"upload": ("demo.emicpkg", archive.read_bytes(), "application/zip")},
    )
    overview = await ac.get("/api/modules/packages/store/overview", headers=headers)
    assert overview.status_code == 200
    body = overview.json()
    assert any(item["module_id"] == "integration.demo" for item in body["installed"])
    assert body["allow_unsigned_modules"] is True
    assert isinstance(body["catalog"], list)


@pytest.mark.asyncio
async def test_validate_unsigned_blocked_in_prod_mode(tmp_path) -> None:
    db_file = tmp_path / "prod-validate.db"
    modules_path = tmp_path / "modules"
    settings = Settings(
        _env_file=None,
        APP_ENV="production",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_MODULES_PATH=str(modules_path),
        EMIC_ALLOW_UNSIGNED_MODULES=False,
        EMIC_ADMIN_TOKEN="admin-secret",
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": "Bearer admin-secret"}
        archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
        res = await ac.post(
            "/api/modules/packages/validate",
            headers=headers,
            files={"upload": ("demo.emicpkg", archive.read_bytes(), "application/zip")},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["install_allowed"] is False
        assert "SIGNATURE_INVALID" in body["errors"]
    await engine.dispose()


@pytest.mark.asyncio
async def test_catalog_validate_and_impact(store_api_client) -> None:
    ac, _, _ = store_api_client
    headers = {"Authorization": "Bearer admin-secret"}
    validate = await ac.post("/api/modules/packages/catalog/integration.demo-1.0.0/validate", headers=headers)
    assert validate.status_code == 200
    impact = await ac.post("/api/modules/packages/catalog/integration.demo-1.0.0/impact", headers=headers)
    assert impact.status_code == 200
    assert impact.json()["module_id"] == "integration.demo"


@pytest.mark.asyncio
async def test_store_package_detail(store_api_client) -> None:
    ac, _, _ = store_api_client
    headers = {"Authorization": "Bearer admin-secret"}
    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
    await ac.post(
        "/api/modules/packages/install",
        headers=headers,
        files={"upload": ("demo.emicpkg", archive.read_bytes(), "application/zip")},
    )
    detail = await ac.get("/api/modules/packages/store/packages/integration.demo", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["module_id"] == "integration.demo"
    assert "publisher_status" in body


@pytest.mark.asyncio
async def test_quarantined_package_enable_blocked(store_api_client) -> None:
    ac, settings, session_factory = store_api_client
    headers = {"Authorization": "Bearer admin-secret"}
    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
    await ac.post(
        "/api/modules/packages/install",
        headers=headers,
        files={"upload": ("demo.emicpkg", archive.read_bytes(), "application/zip")},
    )
    from energy_core.db.installed_package_repo import InstalledPackageRepository
    from energy_core.platform.modules.bootstrap import register_default_modules
    from energy_core.platform.modules.packages.loader import load_installed_module_packages
    from energy_core.platform.modules.packages.quarantine import quarantine_package
    from energy_core.platform.modules.registry import default_module_registry

    register_default_modules()
    default_module_registry.clear()
    try:
        await load_installed_module_packages(session_factory, settings=settings)
        async with session_factory() as session:
            repo = InstalledPackageRepository(session)
            record = await repo.get("integration.demo")
            assert record is not None
            await quarantine_package(session, record, reason="test_quarantine", last_error="blocked in test")
        enable = await ac.put(
            "/api/sites/akarp/modules/integration.demo",
            headers=headers,
            json={"enabled": True},
        )
        assert enable.status_code == 409
        assert enable.json()["detail"]["code"] == "PACKAGE_QUARANTINED"
    finally:
        _restore_default_registry()


@pytest.mark.asyncio
async def test_publisher_add_and_revoke(store_api_client) -> None:
    ac, _, _ = store_api_client
    headers = {"Authorization": "Bearer admin-secret"}
    _, public_key = generate_ed25519_keypair()
    created = await ac.post(
        "/api/modules/publishers",
        headers=headers,
        json={
            "publisher_id": "emic-internal",
            "key_id": "demo-key",
            "public_key_hex": public_key.hex(),
        },
    )
    assert created.status_code == 201
    listed = await ac.get("/api/modules/publishers", headers=headers)
    assert listed.status_code == 200
    assert any(row["publisher_id"] == "emic-internal" for row in listed.json())
    revoked = await ac.post("/api/modules/publishers/emic-internal/demo-key/revoke", headers=headers)
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    retrusted = await ac.post(
        "/api/modules/publishers",
        headers=headers,
        json={
            "publisher_id": "emic-internal",
            "key_id": "demo-key",
            "public_key_hex": public_key.hex(),
        },
    )
    assert retrusted.status_code == 201
    assert retrusted.json()["status"] == "trusted"


@pytest.mark.asyncio
async def test_package_enabled_only_on_selected_site(store_api_client) -> None:
    ac, settings, session_factory = store_api_client
    headers = {"Authorization": "Bearer admin-secret"}
    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
    install = await ac.post(
        "/api/modules/packages/install",
        headers=headers,
        files={"upload": ("demo.emicpkg", archive.read_bytes(), "application/zip")},
    )
    assert install.status_code == 200

    from energy_core.platform.modules.bootstrap import register_default_modules
    from energy_core.platform.modules.packages.loader import load_installed_module_packages
    from energy_core.platform.modules.registry import default_module_registry

    register_default_modules()
    default_module_registry.clear()
    try:
        await load_installed_module_packages(session_factory, settings=settings)

        enable_akarp = await ac.put(
            "/api/sites/akarp/modules/integration.demo",
            headers=headers,
            json={"enabled": True},
        )
        assert enable_akarp.status_code == 200

        disable_denmark = await ac.put(
            "/api/sites/summer-house-denmark/modules/integration.demo",
            headers=headers,
            json={"enabled": False},
        )
        assert disable_denmark.status_code == 200

        activations = await ac.get("/api/modules/packages/integration.demo/sites", headers=headers)
        assert activations.status_code == 200
        by_slug = {row["site_slug"]: row for row in activations.json()}
        assert by_slug["akarp"]["enabled"] is True
        assert by_slug["summer-house-denmark"]["enabled"] is False

        akarp_modules = await ac.get("/api/sites/akarp/modules", headers=headers)
        denmark_modules = await ac.get("/api/sites/summer-house-denmark/modules", headers=headers)
        akarp_demo = next(item for item in akarp_modules.json()["modules"] if item["module_id"] == "integration.demo")
        denmark_demo = next(
            item for item in denmark_modules.json()["modules"] if item["module_id"] == "integration.demo"
        )
        assert akarp_demo["enabled"] is True
        assert denmark_demo["enabled"] is False
    finally:
        _restore_default_registry()
