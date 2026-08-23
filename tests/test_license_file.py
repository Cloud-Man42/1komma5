"""Contract tests for the repository-root ``LICENSE`` file (GH-18).

These tests describe the licensing contract of the whole monorepo, not any
single workspace package, which is why they live in a repo-level ``tests/``
tree rather than under ``backend/tests``, ``collector/tests`` or
``packages/energy-core/tests``.

They verify that:

1. A ``LICENSE`` file exists at the repository root.
2. It identifies itself as the Apache License, Version 2.0 (January 2004).
3. Its copyright line is filled in with the project's actual copyright
   notice -- no template placeholder tokens remain.
4. Its body is otherwise byte-identical, line by line, to the canonical
   Apache-2.0 template published by the Apache Software Foundation. Only the
   single copyright placeholder line may differ; the rest of the legal text
   must never be edited.

The canonical template used for comparison is vendored at
``tests/fixtures/apache-2.0-template.txt`` so this suite is self-contained
and does not depend on any file outside the repository.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LICENSE_PATH = REPO_ROOT / "LICENSE"
TEMPLATE_PATH = Path(__file__).resolve().parent / "fixtures" / "apache-2.0-template.txt"

EXPECTED_COPYRIGHT_LINE = "   Copyright 2026 Henrik Melén and contributors"
PLACEHOLDER_MARKERS = ("[yyyy]", "[name of copyright owner]")


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def test_license_file_exists_at_repo_root() -> None:
    """Given the repository root, when looking for LICENSE, then it must exist."""
    assert LICENSE_PATH.is_file(), (
        f"Expected an Apache-2.0 LICENSE file at {LICENSE_PATH}, but none was found."
    )


def test_license_declares_apache_license_version_2() -> None:
    """Given LICENSE, when its content is read, then it must identify itself
    as the Apache License, Version 2.0 (January 2004)."""
    content = LICENSE_PATH.read_text(encoding="utf-8")

    assert "Apache License" in content
    assert "Version 2.0, January 2004" in content


def test_license_copyright_line_has_no_unresolved_placeholder_tokens() -> None:
    """Given LICENSE, when its content is read, then no unresolved template
    placeholder token (``[yyyy]`` / ``[name of copyright owner]``) may remain."""
    content = LICENSE_PATH.read_text(encoding="utf-8")

    for marker in PLACEHOLDER_MARKERS:
        assert marker not in content, (
            f"LICENSE still contains the unresolved placeholder token {marker!r}; "
            "the copyright line must be filled in with the project's actual "
            "copyright notice."
        )


def test_license_copyright_line_matches_decided_owner_and_year() -> None:
    """Given LICENSE, when its content is read, then the copyright line must
    read exactly 'Copyright 2026 Henrik Melén and contributors', matching the
    notice decided by the repository owner."""
    content = LICENSE_PATH.read_text(encoding="utf-8")

    assert EXPECTED_COPYRIGHT_LINE in content, (
        f"Expected LICENSE to contain the copyright line {EXPECTED_COPYRIGHT_LINE!r}."
    )


def test_license_body_matches_canonical_apache_2_text_except_copyright_line() -> None:
    """Given LICENSE, when compared line by line against the canonical
    Apache-2.0 template, then every line must be identical except the single
    copyright placeholder line, which must be filled in rather than edited
    elsewhere in the text."""
    template_lines = _read_lines(TEMPLATE_PATH)
    license_lines = _read_lines(LICENSE_PATH)

    assert len(license_lines) == len(template_lines), (
        "LICENSE has a different number of lines than the canonical Apache-2.0 "
        f"template ({len(license_lines)} vs {len(template_lines)}); the license "
        "text must not be edited beyond filling in the copyright line."
    )

    mismatches = [
        (line_number, template_line, license_line)
        for line_number, (template_line, license_line) in enumerate(
            zip(template_lines, license_lines), start=1
        )
        if not all(marker in template_line for marker in PLACEHOLDER_MARKERS)
        and template_line != license_line
    ]

    assert not mismatches, (
        "LICENSE text diverges from the canonical Apache-2.0 template outside "
        f"of the copyright line: {mismatches!r}"
    )
