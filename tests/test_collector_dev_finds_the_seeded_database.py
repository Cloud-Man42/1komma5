"""Tests for issue #53: `collector-dev`'s recipe must open the same physical
database file a developer's seeded `energy-dev.db` actually lives in,
regardless of the working directory the recipe happens to run the collector
from.

`.env.example:2` documents a *relative* sqlite `DATABASE_URL`
(`sqlite+aiosqlite:///./energy-dev.db`), which the aiosqlite/sqlite3 driver
resolves against the process's current working directory at connection-open
time -- not against "the project" or "the repository root". `Makefile:25-26`
runs `collector-dev` with `--directory collector` in effect, so today its
working directory is `collector/`, not the repository root a developer's
seeded database (created by `make migrate && make seed`) actually lives in.
SQLite creates the file silently if it is missing, so the failure this
produces is `sqlite3.OperationalError: no such table: sites` -- not an
obvious "database not found" error.

The test below does not seed a real database and does not start the
collector itself (a long-running service). Instead, both the recipe run and
a "correct" repo-root reference run execute a short-lived probe -- swapped
in for `collector-dev`'s `python -m app`, and for a corresponding plain
`uv run python` invocation from the repository root -- that builds a real
`energy_core.config.Settings` and a real `energy_core.db.session.create_engine`
(exactly what `Collector.__init__` does) against a `DATABASE_URL` override
this test controls, and reports which physical file it actually opened.
Routing through the real `Settings` and `create_engine`, rather than
reimplementing sqlite's own relative-path resolution rule in the test
itself, means this test keeps measuring the right thing whether issue #53
ends up fixed in the Makefile, in `energy_core.config`, or both -- the
config-level property this depends on is pinned independently by
`packages/energy-core/tests/test_config_database_url_working_directory.py`.

The `DATABASE_URL` override points at a throwaway filename (`_PROBE_DB_NAME`)
that is neither `energy-dev.db` nor anything a developer would recognize,
and `cleanup_probe_database_files` removes it from every location it could
have landed in, so this never touches or leaves behind a real
`energy-dev.db`, in the repository root or in `collector/`.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE_PATH = REPO_ROOT / "Makefile"
COLLECTOR_DIR = REPO_ROOT / "collector"

_MAKE_BINARY = shutil.which("make")
_UV_BINARY = shutil.which("uv")

# Deliberately not "energy-dev.db": this test must never touch or leave
# behind a real developer's seeded database.
_PROBE_DB_NAME = "issue-53-cwd-probe.db"
_PROBE_DATABASE_URL = f"sqlite+aiosqlite:///./{_PROBE_DB_NAME}"

_PROBE_SCRIPT = """\
import asyncio
from pathlib import Path

from energy_core.config import Settings
from energy_core.db.session import create_engine
from sqlalchemy import text


async def main() -> None:
    # _env_file=None: this probe's only job is to report where the
    # DATABASE_URL this test injects via the environment actually resolves
    # to, uncontaminated by whichever .env file (if any) a real developer
    # happens to have on disk.
    settings = Settings(_env_file=None)
    engine = create_engine(settings)
    try:
        async with engine.connect() as conn:
            row = (await conn.execute(text("PRAGMA database_list"))).one()
            print(f"RESOLVED_DB_FILE={Path(row.file).resolve()}")
    finally:
        await engine.dispose()


asyncio.run(main())
"""


def _collector_dev_recipe_line() -> str:
    """`collector-dev`'s single recipe line, with its leading tab stripped."""
    lines = MAKEFILE_PATH.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.rstrip() == "collector-dev:":
            recipe = lines[index + 1]
            assert recipe.startswith("\t"), (
                f"expected a tab-indented recipe line after 'collector-dev:' in {MAKEFILE_PATH}, "
                f"got {recipe!r}"
            )
            return recipe[1:]
    raise AssertionError(
        f"{MAKEFILE_PATH} has no 'collector-dev:' target; update this test if it was renamed."
    )


def _probe_env() -> dict[str, str]:
    env = dict(os.environ)
    env["DATABASE_URL"] = _PROBE_DATABASE_URL
    return env


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=60, check=False
    )


def _extract_resolved_file(completed: subprocess.CompletedProcess[str], *, context: str) -> Path:
    assert completed.returncode == 0, (
        f"{context} exited {completed.returncode}.\n--- stdout ---\n{completed.stdout}\n"
        f"--- stderr ---\n{completed.stderr}"
    )
    match = re.search(r"^RESOLVED_DB_FILE=(.+)$", completed.stdout, re.MULTILINE)
    assert match, (
        f"{context} printed no RESOLVED_DB_FILE= marker.\n--- stdout ---\n{completed.stdout}"
    )
    return Path(match.group(1).strip())


@pytest.fixture
def probe_script(tmp_path: Path) -> Path:
    script_path = tmp_path / "resolve_db.py"
    script_path.write_text(_PROBE_SCRIPT, encoding="utf-8")
    return script_path


@pytest.fixture
def cleanup_probe_database_files():
    """`collector-dev`'s recipe unavoidably runs `uv run` rooted at the real
    repository (it needs the real project's environment to import
    `energy_core`), so the probe's throwaway database can land in the real
    repository root or in the real `collector/` -- never as `energy-dev.db`,
    but this removes it from both possible locations regardless of which one
    it actually used."""
    yield
    for directory in (REPO_ROOT, COLLECTOR_DIR):
        (directory / _PROBE_DB_NAME).unlink(missing_ok=True)


def test_collector_dev_recipe_opens_the_same_database_file_as_running_from_the_repository_root(
    tmp_path: Path, probe_script: Path, cleanup_probe_database_files: None
) -> None:
    """
    Given `collector-dev`'s recipe exactly as written in the Makefile,
    When it is run the way `make collector-dev` runs it -- only its
    `python -m app` replaced by a probe that reports which physical sqlite
    file its `Settings`/`create_engine` actually opens, every other token
    (including wherever `--directory collector` currently sits) left
    untouched -- and compared against the same probe run as a plain
    `uv run python` invocation from the repository root,
    Then both must open the exact same physical database file. A
    developer's seeded database (created by `make migrate && make seed`)
    only exists at the repository root; if the recipe opens a different
    file, the collector starts against a brand-new, empty database instead
    and fails the first time it queries a table that was never created.
    """
    if _MAKE_BINARY is None:
        pytest.skip("make is not on PATH; cannot exercise the Makefile's recipe environment.")
    if _UV_BINARY is None:
        pytest.skip("uv is not on PATH; cannot exercise a uv-running Makefile recipe.")

    env = _probe_env()

    original_line = _collector_dev_recipe_line()
    substituted = original_line.replace("python -m app", f"python {shlex.quote(str(probe_script))}")
    assert substituted != original_line, (
        f"expected the substring 'python -m app' in collector-dev's recipe {original_line!r}; "
        "update this test's substitution if the recipe's command changed."
    )
    wrapper_path = tmp_path / "probe.mk"
    wrapper_path.write_text(
        f"include {MAKEFILE_PATH}\n\n.PHONY: _issue53_probe\n_issue53_probe:\n\t@{substituted}\n",
        encoding="utf-8",
    )
    recipe_probe = _run(
        [
            "make",
            "--no-print-directory",
            "-f",
            str(wrapper_path),
            "-C",
            str(REPO_ROOT),
            "_issue53_probe",
        ],
        cwd=REPO_ROOT,
        env=env,
    )
    resolved_from_recipe = _extract_resolved_file(
        recipe_probe, context="collector-dev's recipe (python -m app swapped for the probe)"
    )

    repo_root_probe = _run(["uv", "run", "python", str(probe_script)], cwd=REPO_ROOT, env=env)
    resolved_from_repo_root = _extract_resolved_file(
        repo_root_probe,
        context="the same probe run as a plain `uv run python` invocation from the repository root",
    )

    assert resolved_from_recipe == resolved_from_repo_root, (
        f"collector-dev's recipe opened {resolved_from_recipe}, but running the same probe from "
        f"the repository root opened {resolved_from_repo_root}. A developer's seeded database "
        "only exists at the repository root, so the recipe would silently start the collector "
        "against a fresh, empty database instead -- surfacing later as "
        "`sqlite3.OperationalError: no such table: sites` rather than as an obvious "
        "'database not found'."
    )
