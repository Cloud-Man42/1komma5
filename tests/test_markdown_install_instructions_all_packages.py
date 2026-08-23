"""Repository-wide guard against bare `uv sync` install instructions in
markdown documentation (GH-19, generalizing GH-13).

This is the third time the same class of defect has surfaced in this
repository's documentation:

- GH-13: `uv sync` without `--all-packages` in the Makefile, README.md and
  the CI workflow -- all three had to be found and fixed individually
  (see `tests/test_workspace_install.py`, which pins those three specific
  surfaces).
- GH-14: `--directory` placed after the command it was meant to configure,
  in both the Makefile and README.md.
- GH-19: `CONTRIBUTING.md` is a fourth surface that will show a `uv sync`
  command to a contributor, and nothing previously guarded against it (or
  any future markdown document) repeating the GH-13 mistake.

Rather than adding a fourth hand-picked file to guard, this module scans
every markdown file actually checked into the repository (excluding
vendored/build/dependency directories, the same set `.gitignore` already
excludes from version control) and asserts that every runnable `uv sync`
command in them includes `--all-packages`. This automatically covers
`CONTRIBUTING.md` the moment it exists, and covers whatever markdown
document mentions `uv sync` next -- without needing a new test written for
it.

What counts as a runnable command is decided by
`tests/_uv_sync_command_scan.py`, shared with
`tests/test_contribution_governance_docs.py` so the two guards cannot drift
apart: a `uv sync` at the start of a line anywhere in the document, or one
after a shell separator (`&&`, `||`, `;`, `|`) inside a fenced code block.
Chained commands are the shape a line-anchored regex missed while this
docstring already claimed to cover them; see `_uv_sync_command_scan` for why
separator splitting stops at the fence, and
`tests/test_uv_sync_command_scan.py` for the cases that pin both halves.

`tests/test_contribution_governance_docs.py` additionally pins this
specifically for `CONTRIBUTING.md` (AC4's literal target), so that a single
clear failure names the exact acceptance criterion when only that document
regresses; this module is the general safety net around it and every other
document.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _uv_sync_command_scan import UvSyncCommand, command_tokens, find_uv_sync_commands

REPO_ROOT = Path(__file__).resolve().parents[1]

ALL_PACKAGES_FLAG = "--all-packages"

# Directory names excluded from the markdown scan. This list was verified at
# authoring time to make a plain `Path.rglob("*.md")` walk return exactly
# the same five files as `git ls-files '*.md'` (README.md,
# docs/integrations/arctic-spa-api.md, docs/semp/README.md,
# packages/energy-core/src/energy_core/chargers/METERING.md,
# packages/energy-core/src/energy_core/sungrow/conventions.md), i.e. it
# mirrors what `.gitignore` already excludes from version control plus
# `.git` itself. Walking the filesystem directly (rather than shelling out
# to `git ls-files`) means this test also sees a newly created but not yet
# `git add`-ed `CONTRIBUTING.md`.
EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".next",
        ".idea",
        ".cursor",
        "dist",
        "build",
        "out",
        "coverage",
        "htmlcov",
        ".mypy_cache",
    }
)


def _iter_repo_markdown_files(root: Path) -> list[Path]:
    """Return every `*.md` file under `root`, skipping vendored/build
    directories (see `EXCLUDED_DIR_NAMES`), sorted for a deterministic
    parametrization order."""
    return sorted(
        path
        for path in root.rglob("*.md")
        if not any(part in EXCLUDED_DIR_NAMES for part in path.relative_to(root).parts)
    )


def _uv_sync_commands_in(path: Path) -> list[UvSyncCommand]:
    """Return every runnable `uv sync` command in the markdown file at
    `path`, as `(line number, source line, command segment)` triples (see
    `_uv_sync_command_scan.find_uv_sync_commands`)."""
    return find_uv_sync_commands(path.read_text(encoding="utf-8"))


def _discover_uv_sync_command_occurrences() -> list[pytest.param]:
    """Collected at module import time: one parametrize case per
    `(file, line number)` pair across the whole repository where a literal
    `uv sync` command appears, so a failure names the exact file and line
    without needing to re-scan the tree."""
    cases: list[pytest.param] = []
    for path in _iter_repo_markdown_files(REPO_ROOT):
        relative = path.relative_to(REPO_ROOT)
        for found in _uv_sync_commands_in(path):
            cases.append(
                pytest.param(
                    path,
                    found.line_number,
                    found.line,
                    found.command,
                    id=f"{relative}:{found.line_number}",
                )
            )
    return cases


UV_SYNC_OCCURRENCES = _discover_uv_sync_command_occurrences()


def test_at_least_one_uv_sync_command_is_documented_somewhere() -> None:
    """Given the repository's markdown documentation, when scanned for
    literal `uv sync` commands, then at least one must be found (README.md
    has shown one since GH-13 was fixed). This is a sanity check on the
    scan itself: if it ever finds zero occurrences, the regex or the
    exclusion list has silently broken, and every other test in this module
    would pass vacuously without checking anything."""
    assert UV_SYNC_OCCURRENCES, (
        "Expected at least one literal 'uv sync' command across the repository's markdown "
        "documentation (README.md has documented one since GH-13); found none. This most "
        "likely means the scan itself is broken (wrong regex or over-broad exclusion), not "
        "that every 'uv sync' mention has been removed."
    )


@pytest.mark.parametrize("path, line_number, line, command", UV_SYNC_OCCURRENCES)
def test_documented_uv_sync_command_includes_all_packages_flag(
    path: Path, line_number: int, line: str, command: str
) -> None:
    """Given a markdown file anywhere in the repository, when a line in it
    shows a literal `uv sync` command, then that command must include
    `--all-packages` -- `uv sync` alone only installs the root project
    (whose `[project] dependencies` list is empty) and the `dev` group, not
    the workspace members (`packages/energy-core`, `backend`, `collector`),
    so a bare `uv sync` documents a setup flow that cannot actually run the
    application or its test suite (GH-13)."""
    assert ALL_PACKAGES_FLAG in command_tokens(command), (
        f"{path.relative_to(REPO_ROOT)}:{line_number} shows {line!r}; expected the `uv sync` "
        f"command in it ({command!r}) to include {ALL_PACKAGES_FLAG!r} so a reader following "
        "this instruction installs the workspace members alongside the root project and dev "
        "group (GH-13)."
    )
