"""Contract tests for `.github/dependabot.yml` (GH-19).

Dependabot's own ecosystem identifier for `uv` projects is the literal
string `"uv"` -- verified at authoring time against the ground truth,
`dependabot/dependabot-core`'s `PACKAGE_MANAGER_LOOKUP` table in
`common/lib/dependabot/config/file.rb` (fetched via `gh api
repos/dependabot/dependabot-core/contents/...`), which maps the
`package-ecosystem:` value a user writes in `dependabot.yml` to Dependabot's
internal package-manager name: `"uv" => "uv"`, `"npm" => "npm_and_yarn"`,
`"github-actions" => "github_actions"`. This module asserts against the
external `package-ecosystem:` keys (`"uv"`, `"npm"`, `"github-actions"`),
i.e. exactly what a human author writes in the file, not Dependabot's
internal names.

This module holds four groups of tests:

1. Existence (AC2): `.github/dependabot.yml` must exist.
2. Structural validity (AC3): it must parse as valid YAML, declare
   `version: 2`, and have a non-empty `updates` list.
3. Ecosystem coverage (AC3): `updates` must include at least one entry for
   each of the three ecosystems this project actually uses --
   `uv` (the workspace's single root `pyproject.toml`/`uv.lock`), `npm`
   (`frontend/package.json`/`package-lock.json`), and `github-actions`
   (`.github/workflows/`) -- and each entry's `directory` must resolve to
   the location that ecosystem's manifest actually lives at (verified
   at authoring time: a single `uv.lock` at the repo root, a single
   `package-lock.json` under `frontend/`), with a valid `schedule.interval`.
4. Path-traversal guard (security-relevant negative path): no update
   entry's `directory` may resolve outside the repository root. This is a
   real, not theoretical, input-validation boundary: `dependabot.yml` is a
   contributor-editable config file that GitHub's Dependabot service reads
   and acts on.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPENDABOT_PATH = REPO_ROOT / ".github" / "dependabot.yml"

VALID_SCHEDULE_INTERVALS = frozenset({"daily", "weekly", "monthly"})

# One entry per ecosystem this project actually uses, mapping Dependabot's
# external `package-ecosystem:` value to the manifest file that must exist
# in the directory that ecosystem's update entry declares. `github-actions`
# has no directory-local manifest to check: Dependabot always scans
# `.github/workflows/` regardless of the configured `directory`, so only
# its `schedule.interval` is checked, in the ecosystem-coverage test below.
ECOSYSTEM_MANIFEST_MARKERS: dict[str, str] = {
    "uv": "pyproject.toml",
    "npm": "package.json",
}
EXPECTED_ECOSYSTEMS = frozenset({"uv", "npm", "github-actions"})


def _load_dependabot_config() -> dict[str, Any]:
    content = DEPENDABOT_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    assert isinstance(data, dict), f"{DEPENDABOT_PATH} must parse to a YAML mapping."
    return data


def _updates(config: dict[str, Any]) -> list[dict[str, Any]]:
    updates = config.get("updates")
    assert isinstance(updates, list) and updates, (
        f"{DEPENDABOT_PATH} must declare a non-empty 'updates' list."
    )
    return updates


def test_dependabot_config_exists() -> None:
    """Given `.github/`, when looking for `dependabot.yml`, then it must
    exist."""
    assert DEPENDABOT_PATH.is_file(), f"Expected {DEPENDABOT_PATH} to exist."


def test_dependabot_config_is_valid_yaml_with_version_2() -> None:
    """Given `dependabot.yml`, when parsed as YAML, then it must succeed
    and declare `version: 2` -- the only schema version Dependabot
    currently accepts."""
    config = _load_dependabot_config()
    assert config.get("version") == 2, (
        f"{DEPENDABOT_PATH} must declare 'version: 2'; got {config.get('version')!r}."
    )


def test_dependabot_config_declares_a_non_empty_updates_list() -> None:
    """Given `dependabot.yml`, when its top-level `updates` key is read,
    then it must be a non-empty list -- an empty or missing `updates` list
    configures Dependabot to update nothing."""
    config = _load_dependabot_config()
    _updates(config)  # asserts internally


def test_dependabot_covers_every_ecosystem_this_project_actually_uses() -> None:
    """Given `dependabot.yml`'s `updates` list, when the set of configured
    `package-ecosystem` values is read, then it must be a superset of
    `{"uv", "npm", "github-actions"}` -- the three ecosystems this
    monorepo actually has manifests for (a `uv` workspace, an `npm`
    frontend, and GitHub Actions workflows)."""
    config = _load_dependabot_config()
    updates = _updates(config)
    ecosystems_present = {entry.get("package-ecosystem") for entry in updates}

    missing = EXPECTED_ECOSYSTEMS - ecosystems_present
    assert not missing, (
        f"{DEPENDABOT_PATH} is missing 'updates' entries for package-ecosystem(s): "
        f"{sorted(missing)}. Configured ecosystems: {sorted(e for e in ecosystems_present if e)}."
    )


@pytest.mark.parametrize("ecosystem", sorted(EXPECTED_ECOSYSTEMS))
def test_dependabot_ecosystem_entry_has_a_valid_schedule(ecosystem: str) -> None:
    """Given a `package-ecosystem` this project uses, when its `updates`
    entry/entries are read, then each must declare a `schedule.interval`
    that is one of Dependabot's accepted values (`daily`, `weekly`,
    `monthly`), so the entry actually configures a working update
    schedule."""
    config = _load_dependabot_config()
    updates = _updates(config)
    entries = [entry for entry in updates if entry.get("package-ecosystem") == ecosystem]
    assert entries, f"No 'updates' entry found for package-ecosystem {ecosystem!r}."

    for entry in entries:
        schedule = entry.get("schedule")
        interval = schedule.get("interval") if isinstance(schedule, dict) else None
        assert interval in VALID_SCHEDULE_INTERVALS, (
            f"{DEPENDABOT_PATH}'s {ecosystem!r} entry has schedule.interval={interval!r}; "
            f"expected one of {sorted(VALID_SCHEDULE_INTERVALS)}."
        )


@pytest.mark.parametrize("ecosystem", sorted(ECOSYSTEM_MANIFEST_MARKERS))
def test_dependabot_ecosystem_directory_points_at_the_real_manifest_location(
    ecosystem: str,
) -> None:
    """Given the `uv` or `npm` ecosystem's `updates` entry, when its
    `directory` is resolved relative to the repository root, then the
    manifest file that ecosystem actually manages (`pyproject.toml` for
    `uv`, `package.json` for `npm`) must exist there -- verified at
    authoring time: a single `uv.lock` at the repo root (the `uv` workspace
    has one lockfile, not one per member) and a single `package-lock.json`
    under `frontend/`. A `directory` pointing anywhere else would make
    Dependabot silently open pull requests against a manifest that either
    does not exist or is not the one actually locked."""
    config = _load_dependabot_config()
    updates = _updates(config)
    entries = [entry for entry in updates if entry.get("package-ecosystem") == ecosystem]
    assert entries, f"No 'updates' entry found for package-ecosystem {ecosystem!r}."

    marker = ECOSYSTEM_MANIFEST_MARKERS[ecosystem]
    for entry in entries:
        directory = entry.get("directory")
        assert isinstance(directory, str) and directory.startswith("/"), (
            f"{DEPENDABOT_PATH}'s {ecosystem!r} entry has directory={directory!r}; expected an "
            "absolute-style path starting with '/' (Dependabot's convention)."
        )
        resolved = (REPO_ROOT / directory.lstrip("/")).resolve()
        assert (resolved / marker).is_file(), (
            f"{DEPENDABOT_PATH}'s {ecosystem!r} entry declares directory={directory!r} "
            f"(resolves to {resolved}), but no {marker!r} was found there."
        )


def test_dependabot_no_update_entry_directory_escapes_the_repository_root() -> None:
    """Given every entry in `dependabot.yml`'s `updates` list (regardless
    of ecosystem), when each entry's `directory` is resolved relative to
    the repository root, then the result must never fall outside the
    repository root. `dependabot.yml` is a contributor-editable config
    file that GitHub's Dependabot service reads and acts on; a `directory`
    value containing `..` segments that escape the repository is an input
    a malicious or mistaken PR could introduce, and it should be rejected
    by this contract regardless of which ecosystem it is attached to."""
    config = _load_dependabot_config()
    updates = _updates(config)

    for entry in updates:
        directory = str(entry.get("directory", ""))
        resolved = (REPO_ROOT / directory.lstrip("/")).resolve()
        assert resolved.is_relative_to(REPO_ROOT), (
            f"{DEPENDABOT_PATH}'s {entry.get('package-ecosystem')!r} entry declares "
            f"directory={directory!r}, which resolves to {resolved} -- outside the repository "
            f"root ({REPO_ROOT}). A Dependabot 'directory' must never traverse above the repo "
            "it configures."
        )
