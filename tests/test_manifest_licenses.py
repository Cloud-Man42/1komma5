"""Contract tests verifying every workspace manifest declares the Apache-2.0
license (GH-18), keeping package metadata in sync with the repository-root
``LICENSE`` grant asserted in ``tests/test_license_file.py``.

Covers the Python workspace members (root ``pyproject.toml`` plus
``backend``, ``collector`` and ``packages/energy-core``) and the frontend
package (``frontend/package.json``).
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SPDX_ID = "Apache-2.0"

PYPROJECT_MANIFESTS = [
    REPO_ROOT / "pyproject.toml",
    REPO_ROOT / "backend" / "pyproject.toml",
    REPO_ROOT / "collector" / "pyproject.toml",
    REPO_ROOT / "packages" / "energy-core" / "pyproject.toml",
]
FRONTEND_MANIFEST = REPO_ROOT / "frontend" / "package.json"


def _license_field_from_pyproject(path: Path) -> str | None:
    """Extract the effective license identifier from a pyproject.toml's
    [project] table, accepting either the modern bare-SPDX-string form
    (``license = "Apache-2.0"``) or the older PEP 621 table form
    (``license = { text = "Apache-2.0" }``), since this test asserts the
    declared license behavior rather than a specific manifest syntax.
    """
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    license_field = data.get("project", {}).get("license")
    if isinstance(license_field, dict):
        return license_field.get("text")
    return license_field


@pytest.mark.parametrize(
    "manifest_path",
    PYPROJECT_MANIFESTS,
    ids=[str(p.relative_to(REPO_ROOT)) for p in PYPROJECT_MANIFESTS],
)
def test_pyproject_manifest_declares_apache_2_license(manifest_path: Path) -> None:
    """Given a workspace pyproject.toml, when its [project] table is read,
    then the license field must declare Apache-2.0."""
    assert manifest_path.is_file(), f"Expected manifest at {manifest_path} to exist."

    license_field = _license_field_from_pyproject(manifest_path)

    assert license_field == EXPECTED_SPDX_ID, (
        f"{manifest_path.relative_to(REPO_ROOT)} declares license={license_field!r}; "
        f"expected {EXPECTED_SPDX_ID!r}."
    )


def test_frontend_package_json_declares_apache_2_license() -> None:
    """Given frontend/package.json, when its license field is read, then it
    must declare Apache-2.0."""
    assert FRONTEND_MANIFEST.is_file(), f"Expected manifest at {FRONTEND_MANIFEST} to exist."

    data = json.loads(FRONTEND_MANIFEST.read_text(encoding="utf-8"))

    assert data.get("license") == EXPECTED_SPDX_ID, (
        f"frontend/package.json declares license={data.get('license')!r}; "
        f"expected {EXPECTED_SPDX_ID!r}."
    )
