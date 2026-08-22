"""Contract and integration tests for the Python side of the repository's
install flow (GH-13).

``uv sync`` run at the workspace root only installs the root project
(``energy-monorepo``, whose ``[project] dependencies`` list is empty) plus
the ``dev`` dependency group. It does **not** install the workspace
*members* declared under ``[tool.uv.workspace] members`` in the root
``pyproject.toml`` -- ``packages/energy-core``, ``backend`` and
``collector``. Reaching those requires ``uv sync --all-packages``.

Three places in this repository invoke (or document) the Python install
step, and all three must request ``--all-packages`` for the resulting
environment to actually be able to run the test suite or the application:

1. The Makefile's ``install`` target (``make install``, the documented
   entry point for local development).
2. README.md's "Windows equivalents (without make)" section, which shows
   the literal ``uv sync`` invocation for developers who don't use ``make``.
3. ``.github/workflows/test.yml``'s ``python`` job, which installs
   dependencies before running pytest in CI.

Tests 1-3 below are static contract checks against those three surfaces.
Test 4 goes further and verifies the property that actually matters: after
running whatever command the Makefile's ``install`` target currently
specifies, in an isolated environment, every workspace member
(``energy-core``, ``energy-backend``, ``energy-collector``) must be
importable. That test is intentionally decoupled from the literal string
``--all-packages`` -- it reads the real recipe out of the Makefile and runs
it, so it fails while the recipe omits the flag and passes once the recipe
includes it, without needing to be edited when the fix lands.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE_PATH = REPO_ROOT / "Makefile"
README_PATH = REPO_ROOT / "README.md"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "test.yml"

ALL_PACKAGES_FLAG = "--all-packages"

# One entry per `[tool.uv.workspace] members` package in the root
# pyproject.toml, paired with a side-effect-free import expression that can
# only succeed if that specific member (and, for the two `app`-named
# members, its own submodule) was actually installed. `backend` and
# `collector` both ship a top-level package literally named `app` with no
# `__init__.py`, so uv's editable installs merge them into a single PEP 420
# namespace package; asserting on their distinct submodules (`app.main` is
# backend-only, `app.collector` is collector-only) avoids the ambiguity a
# bare `import app` would have.
WORKSPACE_MEMBER_IMPORT_CHECKS = [
    pytest.param("energy-core", "energy_core", id="energy-core"),
    pytest.param("energy-backend", "app.main", id="energy-backend"),
    pytest.param("energy-collector", "app.collector", id="energy-collector"),
]


def _install_recipe_sync_command() -> str:
    """Read the Makefile's `install` target and return the literal shell
    command it uses to sync Python dependencies, with the `$(UV)` make
    variable substituted for its resolved value (e.g. "uv sync" or
    "uv sync --all-packages").

    Reading this from the Makefile, rather than hard-coding an expected
    string, is what lets test_workspace_member_is_importable_after_running_the_install_recipe
    track whatever the `install` target actually does.
    """
    content = MAKEFILE_PATH.read_text(encoding="utf-8")

    uv_var_match = re.search(r"^UV\s*\?=\s*(\S+)\s*$", content, re.MULTILINE)
    assert uv_var_match, f"Expected a 'UV ?= ...' variable definition in {MAKEFILE_PATH}."
    uv_binary = uv_var_match.group(1)

    install_match = re.search(r"^install:.*\n((?:\t.*\n?)+)", content, re.MULTILINE)
    assert install_match, (
        f"Expected an 'install:' target with a tab-indented recipe in {MAKEFILE_PATH}."
    )
    recipe_lines = [
        line[1:] for line in install_match.group(1).splitlines() if line.startswith("\t")
    ]

    sync_lines = [line for line in recipe_lines if "sync" in line]
    assert len(sync_lines) == 1, (
        f"Expected exactly one uv-sync line in the 'install' recipe, found {sync_lines!r} "
        f"in {MAKEFILE_PATH}."
    )
    return sync_lines[0].replace("$(UV)", uv_binary).strip()


def test_makefile_install_target_syncs_with_all_packages() -> None:
    """Given the Makefile's `install` target, when its uv-sync recipe line
    is inspected, then it must invoke `uv sync` with `--all-packages`, so
    that `make install` installs the workspace members alongside the root
    project and dev dependencies."""
    command = _install_recipe_sync_command()

    assert ALL_PACKAGES_FLAG in shlex.split(command), (
        f"Makefile 'install' target runs {command!r}; expected it to include "
        f"{ALL_PACKAGES_FLAG!r} so workspace members (energy-core, energy-backend, "
        "energy-collector) are installed, not just the root project and dev group."
    )


def test_readme_direct_uv_sync_command_uses_all_packages() -> None:
    """Given README.md, when the literal `uv sync` command shown for
    developers who bypass `make` (the "Windows equivalents (without make)"
    section) is read, then it must include `--all-packages`, matching the
    behavior `make install` provides."""
    content = README_PATH.read_text(encoding="utf-8")
    direct_sync_lines = [
        line.strip() for line in content.splitlines() if re.match(r"^\s*uv sync\b", line)
    ]

    assert direct_sync_lines, (
        "Expected README.md to show at least one literal 'uv sync' command "
        "(for developers who don't use make); found none."
    )
    for line in direct_sync_lines:
        assert ALL_PACKAGES_FLAG in shlex.split(line), (
            f"README.md shows {line!r} as the direct uv-sync command; expected it to "
            f"include {ALL_PACKAGES_FLAG!r} so a reader following this instruction ends up "
            "with the same installed set as `make install`."
        )


def test_ci_workflow_installs_python_dependencies_with_all_packages() -> None:
    """Given .github/workflows/test.yml, when the `python` job's
    "Install Python dependencies" step is read, then its `run` command must
    include `--all-packages`, so CI actually installs the workspace members
    before running pytest instead of only the root project and dev group."""
    content = WORKFLOW_PATH.read_text(encoding="utf-8")

    # Isolate the `python:` job's block from the rest of the workflow (up to
    # the next top-level job, `frontend:`) so this only inspects the Python
    # job's own install step, not any unrelated `uv sync` elsewhere.
    job_match = re.search(r"\n  python:\n(.*?)\n  frontend:\n", content, re.DOTALL)
    assert job_match, f"Expected a 'python:' job followed by a 'frontend:' job in {WORKFLOW_PATH}."
    python_job_block = job_match.group(1)

    step_match = re.search(
        r"name:\s*Install Python dependencies\s*\n\s*run:\s*(.+)", python_job_block
    )
    assert step_match, (
        "Expected the 'python' job to contain an 'Install Python dependencies' step "
        f"with a 'run:' command in {WORKFLOW_PATH}."
    )
    run_command = step_match.group(1).strip()

    assert ALL_PACKAGES_FLAG in shlex.split(run_command), (
        f".github/workflows/test.yml's 'Install Python dependencies' step runs "
        f"{run_command!r}; expected it to include {ALL_PACKAGES_FLAG!r} so CI installs "
        "the workspace members before running pytest."
    )


@dataclass(frozen=True)
class _SyncedEnvironment:
    """The result of running the Makefile's install recipe's uv-sync command
    into an isolated, throwaway virtual environment."""

    python_executable: Path
    sync_command: str
    sync_result: subprocess.CompletedProcess[str]


def _venv_python_executable(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


@pytest.fixture(scope="module")
def synced_isolated_environment(tmp_path_factory: pytest.TempPathFactory) -> _SyncedEnvironment:
    """Run the Makefile's `install` target's uv-sync command in an isolated
    virtual environment, separate from the repository's own checked-in
    `.venv`, and return where the resulting interpreter lives.

    This deliberately runs only the Python half of `make install` (not
    `cd frontend && npm ci`, `make migrate` or `make seed`): the bug this
    test guards against (GH-13, `ModuleNotFoundError: No module named
    'app'`) is specific to what `uv sync` installs, and a full
    `rm -rf .venv && make install` cycle would pull in the frontend
    toolchain and a migration/seed step that exercise unrelated code paths
    for no added signal here.

    The uv-sync command itself is read from the Makefile rather than
    hard-coded, so this fixture -- and every test that depends on it --
    naturally starts observing the fixed behavior the moment the Makefile's
    `install` target is corrected, without needing to change.

    `--frozen` is appended defensively so this can never rewrite the
    repository's own `uv.lock`; it does not change which packages a given
    lock file resolves to, so it does not affect the property under test.
    """
    uv_executable = shutil.which("uv")
    if uv_executable is None:
        pytest.skip("uv is not on PATH; cannot exercise the install flow.")

    sync_command = _install_recipe_sync_command()
    venv_dir = tmp_path_factory.mktemp("workspace-install-env")

    env = dict(os.environ)
    env["UV_PROJECT_ENVIRONMENT"] = str(venv_dir)

    argv = [*shlex.split(sync_command), "--frozen"]
    result = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )

    assert result.returncode == 0, (
        f"{argv!r} exited with {result.returncode}.\n--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )

    return _SyncedEnvironment(
        python_executable=_venv_python_executable(venv_dir),
        sync_command=sync_command,
        sync_result=result,
    )


@pytest.mark.parametrize("distribution_name, import_target", WORKSPACE_MEMBER_IMPORT_CHECKS)
def test_workspace_member_is_importable_after_running_the_install_recipe(
    synced_isolated_environment: _SyncedEnvironment,
    distribution_name: str,
    import_target: str,
) -> None:
    """Given a clean, isolated environment, when the Makefile install
    target's uv-sync command is run in it, then every workspace member
    (energy-core, energy-backend, energy-collector) must be importable --
    not just the root project and its dev dependency group."""
    probe = subprocess.run(
        [str(synced_isolated_environment.python_executable), "-c", f"import {import_target}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert probe.returncode == 0, (
        f"`import {import_target}` failed after running "
        f"{synced_isolated_environment.sync_command!r} (workspace member {distribution_name!r} "
        f"is not installed/importable).\n--- stderr ---\n{probe.stderr}"
    )
