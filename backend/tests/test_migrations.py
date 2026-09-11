"""Alembic must run against SQLite, the documented default for development.

The rest of the suite builds its schema from SQLAlchemy metadata, so migrations
are only exercised here. Without this test a migration can be PostgreSQL-only
and still leave a fully green suite behind.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from energy_core.db.models import Base
from sqlalchemy import create_engine, inspect, text

from alembic import command

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "alembic" / "versions"


def _alembic_config() -> Config:
    # Built without alembic.ini on purpose: env.py would call fileConfig() and
    # reconfigure logging for the whole test session.
    config = Config()
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    return config


@pytest.fixture
def migrated_sqlite_db(tmp_path, monkeypatch):
    db_file = tmp_path / "migrations.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    command.upgrade(_alembic_config(), "head")
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        yield engine
    finally:
        engine.dispose()


def test_upgrade_head_reaches_the_latest_revision(migrated_sqlite_db):
    expected_head = ScriptDirectory.from_config(_alembic_config()).get_current_head()
    with migrated_sqlite_db.connect() as conn:
        applied = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert applied == expected_head


def test_migrations_create_every_table_the_orm_expects(migrated_sqlite_db):
    tables = set(inspect(migrated_sqlite_db).get_table_names())
    missing = set(Base.metadata.tables) - tables
    assert not missing


def test_heartbeat_settings_seed_row_gets_a_timestamp(migrated_sqlite_db):
    """Regression: a PostgreSQL-only now() default made this INSERT fail on SQLite."""
    with migrated_sqlite_db.connect() as conn:
        row = conn.execute(
            text("SELECT connection_type, updated_at FROM heartbeat_settings WHERE id = 1")
        ).one()
    assert row.connection_type == "mock"
    assert row.updated_at is not None


def test_isolated_runtime_tables_exist_after_head(migrated_sqlite_db):
    """Regression: migration 069 creates isolated runtime persistence tables."""
    tables = set(inspect(migrated_sqlite_db).get_table_names())
    for name in ("isolated_runtime_instances", "runtime_events", "runtime_control_leases"):
        assert name in tables


@pytest.mark.skipif(not __import__("os").environ.get("TEST_POSTGRES_URL"), reason="TEST_POSTGRES_URL required")
def test_upgrade_head_on_postgresql(tmp_path, monkeypatch):
    """Validate Alembic head (including 069) against PostgreSQL semantics."""
    postgres_url = __import__("os").environ["TEST_POSTGRES_URL"]
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    command.upgrade(_alembic_config(), "head")
    engine = create_engine(postgres_url.replace("+asyncpg", "").replace("+psycopg", ""))
    try:
        with engine.connect() as conn:
            applied = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            expected = ScriptDirectory.from_config(_alembic_config()).get_current_head()
            assert applied == expected
            tables = set(inspect(engine).get_table_names())
            assert "isolated_runtime_instances" in tables
    finally:
        engine.dispose()


def test_no_migration_hardcodes_the_postgres_now_function():
    """sa.func.now() renders per dialect; sa.text("now()") is passed through verbatim."""
    literal_now = re.compile(r"""text\(\s*["']now\(\)["']\s*\)""")
    offenders = [
        path.name for path in sorted(VERSIONS_DIR.glob("*.py")) if literal_now.search(path.read_text())
    ]
    assert offenders == []
