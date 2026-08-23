"""Anchoring for configuration values that would otherwise be resolved
against the process's current working directory (GH-53).

Two settings in `energy_core.config.Settings` are written as *relative*
paths -- `database_url`'s default sqlite path (identical to the value
`.env.example` documents) and `env_file`. Neither pydantic-settings nor
SQLAlchemy resolves such a path against "the project": pydantic-settings
opens the env file relative to the cwd, and a relative sqlite URL is handed
verbatim to the aiosqlite/sqlite3 driver, which resolves it against the
cwd at connection-open time. The same configuration therefore selects a
different physical file depending on which directory the process was
started from -- `make collector-dev` runs from `collector/` (`Makefile`'s
`collector-dev` recipe, whose working directory is pinned by
`tests/test_makefile_collector_dev_directory.py`), while `make migrate`
and `make seed` run from the repository root. SQLite creates a missing
file silently, so the symptom is a late
`sqlite3.OperationalError: no such table: sites` rather than an obvious
"database not found".

`project_root()` supplies the fixed anchor that removes the cwd from that
equation. It is deliberately *not* derived from the cwd in any way.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

#: Absolute path override for `project_root()`. Deployments whose layout
#: differs from this repository's workspace layout set this instead of
#: relying on the package-relative fallback.
PROJECT_ROOT_ENV_VAR = "ENERGY_PROJECT_ROOT"

#: The workspace directory every member package lives under, both in this
#: repository (`<root>/packages/energy-core/src/energy_core`) and in the
#: images built by `docker/backend.Dockerfile` and
#: `docker/collector.Dockerfile`, which copy `packages/energy-core` to
#: `/app/packages/energy-core`. Matched by exact name, so the `site-packages`
#: directory of a non-editable install cannot be mistaken for it.
_WORKSPACE_PACKAGES_DIR_NAME = "packages"

_SQLITE_DRIVER_PREFIX = "sqlite"
_SQLITE_IN_MEMORY_DATABASE = ":memory:"
_SQLITE_URI_FILENAME_PREFIX = "file:"

DEFAULT_ENV_FILE_NAME = ".env"


def project_root() -> Path | None:
    """The directory relative paths in the configuration are anchored to, or
    `None` if it cannot be determined.

    Resolution order:

    1. `ENERGY_PROJECT_ROOT`, if set to a non-empty value.
    2. The parent of the `packages/` workspace directory the `energy_core`
       package is installed from -- the repository root under this
       repository's editable workspace install, and `/app` inside the
       images built from `docker/`.

    The current working directory is never consulted: that is the whole
    point of this function.

    Known edge case: step 2 matches on the directory *name* alone. The
    exact-name match is what keeps `site-packages` from being mistaken for
    the workspace directory, but a non-editable install that happened to sit
    under a directory named literally `packages` would still match, and step
    2 would then return that directory's parent instead of falling back to
    `None`. No such layout exists in this repository or in the images built
    from `docker/`, and nothing here detects one; set `ENERGY_PROJECT_ROOT`
    explicitly for a deployment where it could arise.
    """
    override = os.environ.get(PROJECT_ROOT_ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser().resolve()

    for ancestor in Path(__file__).resolve().parents:
        if ancestor.name == _WORKSPACE_PACKAGES_DIR_NAME:
            return ancestor.parent
    return None


def default_env_file() -> Path:
    """The `.env` file `Settings` reads when the caller does not override it.

    Anchored at `project_root()` so that every entry point reads the same
    file. Falls back to the bare relative name when no project root can be
    determined, which is what pydantic-settings did before this module
    existed. A missing env file is ignored by pydantic-settings either way.
    """
    root = project_root()
    return Path(DEFAULT_ENV_FILE_NAME) if root is None else root / DEFAULT_ENV_FILE_NAME


def resolve_database_url(database_url: str) -> str:
    """Return `database_url` with a relative sqlite *file* path rewritten to
    an absolute one anchored at `project_root()`.

    Every other URL is returned byte-identical, including:

    * non-sqlite URLs -- a PostgreSQL URL's `database` component is a
      database *name*, not a path, and rewriting it would be nonsense.
      Such URLs are not even parsed here, so a credential-bearing URL can
      never reach an exception message raised from this module.
    * sqlite URLs that are already absolute, in-memory (`:memory:` or no
      database component at all), or `file:`-style URI filenames, whose
      interpretation belongs to the sqlite driver.

    Raises:
        ValueError: if the URL names a relative sqlite file but no project
            root could be determined to anchor it to. Failing here is
            deliberate: the alternative is sqlite silently creating an
            empty database in whichever directory the process happened to
            start in, which is the failure mode GH-53 is about.
        ValueError: if the URL is sqlite-prefixed and URL-shaped but
            semantically invalid -- a non-numeric port, say. SQLAlchemy's
            own parser raises that one and this function deliberately lets
            it through unchanged; see the `except ArgumentError` clause.
    """
    if not database_url.startswith(_SQLITE_DRIVER_PREFIX):
        return database_url

    try:
        url = make_url(database_url)
    except ArgumentError:
        # `ArgumentError` is what `make_url` reports for a string that is
        # not URL-shaped at all, and it is the only failure caught here.
        # There is then no database component to anchor, so the value is
        # handed on untouched rather than reported as a new kind of
        # failure: `energy_core.db.session.create_engine` still rejects it
        # through SQLAlchemy's own error path, exactly as it did before
        # this anchoring step existed.
        #
        # A URL-shaped but semantically invalid value is deliberately *not*
        # caught. `sqlalchemy.engine.url._parse_url` raises a bare
        # `ValueError` out of `int(components["port"])` for a non-numeric
        # port, and `ArgumentError` is not a `ValueError` subclass, so that
        # one propagates. Letting it is the friendlier behavior of the two:
        # raised from the `database_url` field validator it reaches the
        # developer as a pydantic `ValidationError` that names
        # `DATABASE_URL` and quotes the offending value, whereas catching
        # it would defer the identical message to `create_async_engine`,
        # stripped of any hint of which setting produced it. Widening this
        # to `except (ArgumentError, ValueError)` would additionally
        # swallow any unrelated `ValueError` raised inside `make_url`,
        # hiding genuine parsing bugs.
        return database_url

    database = url.database
    if not database or database == _SQLITE_IN_MEMORY_DATABASE:
        return database_url
    if database.startswith(_SQLITE_URI_FILENAME_PREFIX) or url.query.get("uri") == "true":
        return database_url

    candidate = Path(database)
    if candidate.is_absolute():
        return database_url

    root = project_root()
    if root is None:
        raise ValueError(
            f"the relative sqlite path {database!r} cannot be anchored: the project root could "
            f"not be determined from the installed location of the 'energy_core' package. Set "
            f"{PROJECT_ROOT_ENV_VAR} to an absolute path, or give an absolute sqlite path."
        )

    return url.set(database=str((root / candidate).resolve())).render_as_string(hide_password=False)
