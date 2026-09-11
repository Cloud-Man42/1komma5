"""Module packages API tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.deps import set_session_factory
from app.main import create_app
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.session import create_engine, create_session_factory
from energy_core.seed import seed_sites
from httpx import ASGITransport, AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "packages" / "energy-core" / "tests" / "fixtures" / "modules"


@pytest.fixture
async def package_api_client(tmp_path):
    db_file = tmp_path / "module-packages.db"
    modules_path = tmp_path / "modules"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_MODULES_PATH=str(modules_path),
        EMIC_ALLOW_UNSIGNED_MODULES=True,
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
        yield ac
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_packages_requires_admin(package_api_client) -> None:
    ac = package_api_client
    res = await ac.get("/api/modules/packages")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_package_detail_requires_admin(package_api_client) -> None:
    ac = package_api_client
    headers = {"Authorization": "Bearer admin-secret"}
    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
    await ac.post(
        "/api/modules/packages/install",
        headers=headers,
        files={"upload": ("demo.emicpkg", archive.read_bytes(), "application/zip")},
    )
    anon = await ac.get("/api/modules/packages/integration.demo")
    assert anon.status_code == 401
    detail = await ac.get("/api/modules/packages/integration.demo", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert "package_path" not in body
    assert body["logical_package_id"] == "integration.demo@1.0.0"


@pytest.mark.asyncio
async def test_validate_package_requires_admin(package_api_client) -> None:
    ac = package_api_client
    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
    res = await ac.post(
        "/api/modules/packages/validate",
        files={"upload": ("demo.emicpkg", archive.read_bytes(), "application/zip")},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_validate_and_install_demo_package(package_api_client) -> None:
    ac = package_api_client
    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
    headers = {"Authorization": "Bearer admin-secret"}
    validate = await ac.post(
        "/api/modules/packages/validate",
        headers=headers,
        files={"upload": ("demo.emicpkg", archive.read_bytes(), "application/zip")},
    )
    assert validate.status_code == 200
    assert validate.json()["valid"] is True

    install = await ac.post(
        "/api/modules/packages/install",
        headers=headers,
        files={"upload": ("demo.emicpkg", archive.read_bytes(), "application/zip")},
    )
    assert install.status_code == 200
    body = install.json()
    assert body["success"] is True
    assert body["restart_required"] is True

    listed = await ac.get("/api/modules/packages", headers=headers)
    assert listed.status_code == 200
    assert any(item["module_id"] == "integration.demo" for item in listed.json())


@pytest.mark.asyncio
async def test_install_duplicate_rejected(package_api_client) -> None:
    ac = package_api_client
    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
    headers = {"Authorization": "Bearer admin-secret"}
    await ac.post(
        "/api/modules/packages/install",
        headers=headers,
        files={"upload": ("demo.emicpkg", archive.read_bytes(), "application/zip")},
    )
    dup = await ac.post(
        "/api/modules/packages/install",
        headers=headers,
        files={"upload": ("demo.emicpkg", archive.read_bytes(), "application/zip")},
    )
    assert dup.status_code == 422
    assert dup.json()["detail"]["code"] == "MODULE_ALREADY_INSTALLED"


@pytest.mark.asyncio
async def test_impact_requires_admin(package_api_client) -> None:
    ac = package_api_client
    res = await ac.post("/api/modules/packages/integration.demo/impact")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_impact_remove_report(package_api_client) -> None:
    ac = package_api_client
    headers = {"Authorization": "Bearer admin-secret"}
    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
    await ac.post(
        "/api/modules/packages/install",
        headers=headers,
        files={"upload": ("demo.emicpkg", archive.read_bytes(), "application/zip")},
    )
    impact = await ac.post("/api/modules/packages/integration.demo/impact", headers=headers)
    assert impact.status_code == 200
    body = impact.json()
    assert body["module_id"] == "integration.demo"
    assert body["restart_required"] is True


@pytest.mark.asyncio
async def test_validate_signed_package_uses_trust_store(tmp_path) -> None:
    import zipfile

    from energy_core.platform.modules.packages.signing import generate_ed25519_keypair, sign_package_dir

    db_file = tmp_path / "signed-validate.db"
    modules_path = tmp_path / "modules"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_MODULES_PATH=str(modules_path),
        EMIC_ALLOW_UNSIGNED_MODULES=False,
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
    private_key, public_key = generate_ed25519_keypair()
    extract_dir = tmp_path / "pkg"
    with zipfile.ZipFile(FIXTURES / "integration.demo-1.0.0.emicpkg", "r") as zf:
        zf.extractall(extract_dir)
    sign_package_dir(
        package_dir=extract_dir,
        publisher="emic-internal-test",
        key_id="test-2026-01",
        private_key_pem=private_key,
    )
    signed = tmp_path / "signed.emicpkg"
    with zipfile.ZipFile(signed, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in extract_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(extract_dir).as_posix())
    headers = {"Authorization": "Bearer admin-secret"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        blocked = await ac.post(
            "/api/modules/packages/validate",
            headers=headers,
            files={"upload": ("demo.emicpkg", signed.read_bytes(), "application/zip")},
        )
        assert blocked.status_code == 200
        assert blocked.json()["signature_valid"] is False

        created = await ac.post(
            "/api/modules/publishers",
            headers=headers,
            json={
                "publisher_id": "emic-internal-test",
                "key_id": "test-2026-01",
                "public_key_hex": public_key.hex(),
            },
        )
        assert created.status_code == 201

        validate = await ac.post(
            "/api/modules/packages/validate",
            headers=headers,
            files={"upload": ("demo.emicpkg", signed.read_bytes(), "application/zip")},
        )
        assert validate.status_code == 200
        body = validate.json()
        assert body["signature_valid"] is True
        assert body["publisher_trusted"] is True
        assert body["install_allowed"] is True
    await engine.dispose()
