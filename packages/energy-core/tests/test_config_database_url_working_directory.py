"""Tests for issue #53: `Settings.database_url`'s default sqlite path must
resolve to the same physical file no matter which working directory
`Settings` is instantiated from.

`.env.example:2` documents a *relative* sqlite path --

    DATABASE_URL=sqlite+aiosqlite:///./energy-dev.db

-- and `Settings.database_url`'s own field default (`config.py`) carries the
identical value. A relative sqlite URL is not resolved by `Settings` or by
`energy_core.config` itself: it is handed, as written, to SQLAlchemy's
`create_async_engine` (`energy_core/db/session.py`'s `create_engine`), which
hands it straight to the aiosqlite/sqlite3 driver. That driver resolves a
relative path exactly like any other relative filesystem path -- against the
process's *current working directory at connection-open time*. Nothing in
that chain is aware of "the project" or "the repository root", so the same
`DATABASE_URL` string opens a different physical file depending on which
directory the process happened to be started from -- e.g. `collector-dev`'s
`--directory collector` (`Makefile:25-26`) versus the repository root a
developer's seeded `energy-dev.db` actually lives in.

`_resolved_sqlite_file` below mirrors that resolution rule without opening a
connection, so the tests that use it have no filesystem side effects.
`test_resolved_sqlite_file_matches_a_real_sqlite_connection` is the one test
in this module that actually opens a connection -- entirely inside
`tmp_path`, using a filename unrelated to `energy-dev.db` -- to prove the
mirror is accurate rather than assumed.

`test_settings_database_url_resolves_to_the_same_physical_file_regardless_of_the_instantiating_working_directory`
is AC2 from issue #53: instantiating `Settings` from an arbitrary working
directory must not change which physical database file its `database_url`
denotes. It asserts on `Settings().database_url`'s resolved value rather
than on any particular Makefile recipe, so it captures the underlying
property regardless of whether issue #53 ends up fixed by normalizing
`database_url` itself, by resolving it against a fixed anchor, or by some
other means -- as long as the fix makes the field's *effective* value
cwd-independent. The companion Makefile-level test lives in
`tests/test_collector_dev_finds_the_seeded_database.py`.

The last two tests in this module pin the two ways `make_url` can reject a
sqlite-prefixed value inside `energy_core.paths.resolve_database_url`, which
that function's `except ArgumentError` clause treats deliberately
differently: a value that is not URL-shaped at all is handed through
untouched, while a URL-shaped but semantically invalid one is left to
propagate so it is reported against the `DATABASE_URL` field. Those tests
exist so that the narrow `except` stays a decision rather than becoming an
oversight -- widening it to `except (ArgumentError, ValueError)` fails the
second of them.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from energy_core.config import Settings
from energy_core.paths import resolve_database_url
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import create_async_engine


def _resolved_sqlite_file(database_url: str, working_directory: Path) -> Path:
    """The absolute file `database_url` denotes if a sqlite/aiosqlite
    connection is opened while the process's cwd is `working_directory`.
    Mirrors sqlite3's own relative-path rule (relative to cwd at connection-
    open time) without opening a connection -- see
    `test_resolved_sqlite_file_matches_a_real_sqlite_connection` for the
    empirical check that this mirrors real behavior."""
    raw_database = make_url(database_url).database
    assert raw_database, f"{database_url!r} has no database component to resolve."
    candidate = Path(raw_database)
    return candidate if candidate.is_absolute() else (working_directory / candidate).resolve()


@pytest.mark.asyncio
async def test_resolved_sqlite_file_matches_a_real_sqlite_connection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Given a relative sqlite URL and a working directory entirely inside
    `tmp_path`,
    When a real `aiosqlite` connection is opened from that working directory
    and asked, via `PRAGMA database_list`, which file it actually opened,
    Then that file must be exactly what `_resolved_sqlite_file` computes for
    the same URL and working directory -- proving the hand-rolled resolution
    the other tests in this module rely on matches real sqlite3 behavior
    rather than an assumption about it.
    """
    working_directory = tmp_path / "empirical-check"
    working_directory.mkdir()
    monkeypatch.chdir(working_directory)
    database_url = "sqlite+aiosqlite:///./empirical-check.db"

    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            row = (await conn.execute(text("PRAGMA database_list"))).one()
            actually_opened = Path(row.file).resolve()
    finally:
        await engine.dispose()

    assert actually_opened == _resolved_sqlite_file(database_url, working_directory)


def test_settings_database_url_resolves_to_the_same_physical_file_regardless_of_the_instantiating_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Given `Settings` instantiated with no overrides (its default, relative
    `database_url`, identical to `.env.example`'s documented value),
    When it is instantiated once from a working directory standing in for
    the repository root and once more from an unrelated working directory,
    Then the physical sqlite file its `database_url` resolves to must be the
    same file both times -- a developer's or `make`'s choice of which
    directory to run a command from must not silently select a different
    database.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    repo_root_stand_in = tmp_path / "repo_root_stand_in"
    other_directory = tmp_path / "some" / "other" / "directory"
    repo_root_stand_in.mkdir()
    other_directory.mkdir(parents=True)

    monkeypatch.chdir(repo_root_stand_in)
    database_url = Settings(_env_file=None).database_url
    file_from_repo_root = _resolved_sqlite_file(database_url, repo_root_stand_in)

    monkeypatch.chdir(other_directory)
    file_from_other_directory = _resolved_sqlite_file(
        Settings(_env_file=None).database_url, other_directory
    )

    assert file_from_other_directory == file_from_repo_root, (
        f"Settings().database_url ({database_url!r}) resolves to {file_from_repo_root} from a "
        f"repository-root stand-in but to {file_from_other_directory} from {other_directory}. The "
        "same configuration must not silently point at two different physical databases "
        "depending on which directory a command happens to run from."
    )


def test_settings_database_url_matching_env_example_resolves_the_same_way_via_an_explicit_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Given `Settings` constructed with `DATABASE_URL` set to the exact value
    `.env.example` documents (rather than relying on the field default, so
    this keeps exercising that value even if the default is ever changed to
    something else),
    When it is instantiated from two different working directories,
    Then its `database_url` must resolve to the same physical file both
    times.
    """
    documented_value = "sqlite+aiosqlite:///./energy-dev.db"
    repo_root_stand_in = tmp_path / "repo_root_stand_in"
    other_directory = tmp_path / "other_directory"
    repo_root_stand_in.mkdir()
    other_directory.mkdir()

    monkeypatch.chdir(repo_root_stand_in)
    file_from_repo_root = _resolved_sqlite_file(
        Settings(_env_file=None, DATABASE_URL=documented_value).database_url,
        repo_root_stand_in,
    )

    monkeypatch.chdir(other_directory)
    file_from_other_directory = _resolved_sqlite_file(
        Settings(_env_file=None, DATABASE_URL=documented_value).database_url,
        other_directory,
    )

    assert file_from_other_directory == file_from_repo_root, (
        f".env.example's documented DATABASE_URL ({documented_value!r}) resolves to "
        f"{file_from_repo_root} from a repository-root stand-in but to "
        f"{file_from_other_directory} from {other_directory}."
    )


def test_settings_database_url_that_is_already_absolute_is_unaffected_by_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Given `Settings` constructed with an already-absolute sqlite
    `DATABASE_URL` (four slashes, e.g. what a production deployment would
    set),
    When it is instantiated from two different working directories,
    Then its `database_url` must resolve to the same physical file both
    times. This case never had the bug issue #53 is about, and this test
    stays true before and after any fix, since an absolute path does not
    depend on the working directory at all; it is here to document that
    boundary and guard against a fix that accidentally breaks it.
    """
    absolute_target = tmp_path / "prod-style" / "energy.db"
    absolute_target.parent.mkdir()
    absolute_url = f"sqlite+aiosqlite:///{absolute_target.as_posix()}"

    dir_a = tmp_path / "dir_a"
    dir_b = tmp_path / "dir_b"
    dir_a.mkdir()
    dir_b.mkdir()

    monkeypatch.chdir(dir_a)
    file_from_a = _resolved_sqlite_file(
        Settings(_env_file=None, DATABASE_URL=absolute_url).database_url, dir_a
    )

    monkeypatch.chdir(dir_b)
    file_from_b = _resolved_sqlite_file(
        Settings(_env_file=None, DATABASE_URL=absolute_url).database_url, dir_b
    )

    assert file_from_a == file_from_b == absolute_target.resolve()


def test_a_sqlite_prefixed_value_that_is_not_url_shaped_is_handed_through_untouched() -> None:
    """
    Given a `DATABASE_URL` that starts with `sqlite` but is not URL-shaped
    at all, so `make_url` rejects it with `ArgumentError`,
    When it is passed through `resolve_database_url` and through `Settings`,
    Then it must come back byte-identical -- the anchoring step has no
    database component to work with and must not invent a new kind of
    failure -- and SQLAlchemy must still be the thing that rejects it, at
    engine creation, exactly as it did before the anchoring step existed.
    """
    not_url_shaped = "sqlite-but-not-a-url"
    with pytest.raises(ArgumentError):
        make_url(not_url_shaped)

    assert resolve_database_url(not_url_shaped) == not_url_shaped
    assert Settings(_env_file=None, DATABASE_URL=not_url_shaped).database_url == not_url_shaped

    with pytest.raises(ArgumentError):
        create_async_engine(not_url_shaped)


def test_a_url_shaped_but_invalid_sqlite_url_is_reported_against_the_database_url_field() -> None:
    """
    Given a `DATABASE_URL` that is URL-shaped enough for `make_url`'s regex
    to match but semantically invalid -- a non-numeric port, which makes
    SQLAlchemy's parser raise a bare `ValueError` out of `int()` rather than
    the `ArgumentError` `resolve_database_url` catches,
    When `Settings` is constructed with it,
    Then the failure must surface as a pydantic `ValidationError` naming the
    `DATABASE_URL` field and quoting the offending value, rather than being
    swallowed here and re-emerging later, without that context, at engine
    creation. This pins the deliberate narrowness of `resolve_database_url`'s
    `except ArgumentError`.
    """
    non_numeric_port = "sqlite+aiosqlite://host:notaport/energy-dev.db"

    with pytest.raises(ValueError) as raised_directly:
        resolve_database_url(non_numeric_port)
    assert not isinstance(raised_directly.value, ArgumentError)

    with pytest.raises(ValidationError) as raised_by_settings:
        Settings(_env_file=None, DATABASE_URL=non_numeric_port)

    errors = raised_by_settings.value.errors()
    assert [error["loc"] for error in errors] == [("DATABASE_URL",)]
    assert errors[0]["input"] == non_numeric_port
    assert "notaport" in errors[0]["msg"]
