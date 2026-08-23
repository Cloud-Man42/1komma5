"""Tests for the repository's core contribution-governance documents (GH-19).

The repository is public and already accepts external contributions, but
until GH-19 it shipped none of the documents a contributor or a security
researcher needs: no `CONTRIBUTING.md` (so there was no working setup
instruction beyond trial and error), no `CODE_OF_CONDUCT.md`, and no
`SECURITY.md` (so there was no channel to report a vulnerability other than
a public issue, even though this project talks to third-party credentials
and controls physical hardware).

Repository-level security settings (`vulnerability_alerts`,
`dependabot_security_updates`, `private_vulnerability_reporting`,
`secret_scanning`, `secret_scanning_push_protection`) are configured
out-of-band via the GitHub API and are not covered here -- they have no
corresponding file in the checked-out tree for a test to inspect. This
module only covers the three governance documents that *do* live in the
tree.

This module holds three groups of tests:

1. `test_governance_document_exists_and_is_non_empty` (AC1): each of
   `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` and `SECURITY.md` must exist at
   the repository root and contain more than just whitespace.
2. `test_contributing_install_instruction_uses_all_packages_flag` (AC4):
   every runnable `uv sync` command in `CONTRIBUTING.md` must include
   `--all-packages`. What counts as runnable is decided by the shared
   scanner in `tests/_uv_sync_command_scan.py`, which recognizes a chained
   command (`cd frontend && uv sync`) as well as one standing alone on its
   line. `uv sync` run at the workspace root without that flag only
   installs the root project (`energy-monorepo`, whose `[project]
   dependencies` list is empty) plus the `dev` group -- it does not install
   the workspace members (`packages/energy-core`, `backend`, `collector`),
   which is exactly the GH-13 defect. Documenting the bare command here
   would describe a setup flow that cannot run the test suite or the
   application. See `tests/test_markdown_install_instructions_all_packages.py`
   for the repository-wide version of this same guard, which additionally
   protects every other markdown document (not just this one) against the
   same class of mistake.
3. `test_security_policy_references_a_private_reporting_channel` and
   `test_security_policy_does_not_instruct_public_issue_filing_for_vulnerabilities`
   (AC5): `SECURITY.md` must point a reporter at a private channel (GitHub's
   private vulnerability reporting, which is already enabled for this
   repository, or an email address) and must never instruct a reporter to
   open a public issue to disclose a vulnerability.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from _uv_sync_command_scan import command_tokens, find_uv_sync_commands

REPO_ROOT = Path(__file__).resolve().parents[1]

CONTRIBUTING_PATH = REPO_ROOT / "CONTRIBUTING.md"
CODE_OF_CONDUCT_PATH = REPO_ROOT / "CODE_OF_CONDUCT.md"
SECURITY_PATH = REPO_ROOT / "SECURITY.md"

GOVERNANCE_DOCUMENTS = [
    pytest.param(CONTRIBUTING_PATH, id="CONTRIBUTING.md"),
    pytest.param(CODE_OF_CONDUCT_PATH, id="CODE_OF_CONDUCT.md"),
    pytest.param(SECURITY_PATH, id="SECURITY.md"),
]

ALL_PACKAGES_FLAG = "--all-packages"

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}")

# Any of these substrings (case-insensitive) is accepted evidence that
# SECURITY.md points at a private reporting channel. The first four name
# GitHub's private vulnerability reporting feature, which the repository
# owner has already enabled for this repository (see GH-19's second
# comment); the URL fragment covers a direct link to it.
PRIVATE_REPORTING_MARKERS = (
    "security/advisories",
    "private vulnerability reporting",
    "report a vulnerability",
    "security advisor",  # matches both "security advisory" and "advisories"
)

VULNERABILITY_KEYWORDS = ("vulnerab", "sårbarhet")
NEGATION_MARKERS = ("not ", "n't", "never", "don't", "do not", "inte", "aldrig", "ej ")

# Splits SECURITY.md's content into sentence-ish chunks on sentence-ending
# punctuation or blank lines, so the "no public-issue instruction" check
# below can reason about one claim at a time instead of the whole document,
# and so a negated sentence ("please do NOT open a public issue...") is not
# mistaken for the anti-pattern it is explicitly warning against.
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n{2,}|\n(?=[-*#])")


@pytest.mark.parametrize("path", GOVERNANCE_DOCUMENTS)
def test_governance_document_exists_and_is_non_empty(path: Path) -> None:
    """Given the repository root, when looking for a required governance
    document, then it must exist as a regular file and contain more than
    whitespace, so a contributor opening it finds real guidance rather than
    an empty placeholder."""
    assert path.is_file(), f"Expected {path.name} to exist at the repository root ({path})."
    content = path.read_text(encoding="utf-8")
    assert content.strip() != "", f"{path.name} exists but is empty (or only whitespace)."


def test_contributing_install_instruction_uses_all_packages_flag() -> None:
    """Given CONTRIBUTING.md, when every runnable `uv sync` command in it is
    read -- chained ones included -- then each must carry `--all-packages`,
    so a contributor following the documented setup ends up with the
    workspace members (`energy-core`, `energy-backend`, `energy-collector`)
    actually installed, not just the root project and dev dependency
    group."""
    commands = find_uv_sync_commands(CONTRIBUTING_PATH.read_text(encoding="utf-8"))

    assert commands, (
        "Expected CONTRIBUTING.md to show at least one literal 'uv sync' command as part of "
        "its setup instructions; found none."
    )
    for found in commands:
        assert ALL_PACKAGES_FLAG in command_tokens(found.command), (
            f"CONTRIBUTING.md:{found.line_number} shows {found.line!r} as a setup command; "
            f"expected the `uv sync` in it ({found.command!r}) to include "
            f"{ALL_PACKAGES_FLAG!r} (GH-13) so a contributor following it ends up with the "
            "workspace members installed, not just the root project and dev group."
        )


def test_security_policy_references_a_private_reporting_channel() -> None:
    """Given SECURITY.md, when its content is read, then it must reference
    a private reporting channel -- GitHub's private vulnerability reporting
    (already enabled for this repository) or a contact email address --
    so a security researcher has an actual private path to disclose a
    vulnerability through."""
    content = SECURITY_PATH.read_text(encoding="utf-8")
    lowered = content.lower()

    has_named_channel = any(marker in lowered for marker in PRIVATE_REPORTING_MARKERS)
    has_email_channel = EMAIL_RE.search(content) is not None

    assert has_named_channel or has_email_channel, (
        "Expected SECURITY.md to reference a private reporting channel (GitHub's private "
        "vulnerability reporting / Security Advisories, or a contact email address); found "
        "neither."
    )


def test_security_policy_does_not_instruct_public_issue_filing_for_vulnerabilities() -> None:
    """Given SECURITY.md, when its content is split into sentence-sized
    chunks, then no chunk that talks about a vulnerability may instruct a
    reader to open an issue without also negating that instruction (e.g.
    "please do NOT open a public issue" is fine; "to report a vulnerability,
    open an issue" is not), so the document never sends a security reporter
    down the public disclosure path GH-19 was opened to close off."""
    content = SECURITY_PATH.read_text(encoding="utf-8")
    chunks = [c.strip() for c in SENTENCE_SPLIT_RE.split(content) if c.strip()]

    offending = [
        chunk
        for chunk in chunks
        if any(keyword in chunk.lower() for keyword in VULNERABILITY_KEYWORDS)
        and "issue" in chunk.lower()
        and not any(negation in chunk.lower() for negation in NEGATION_MARKERS)
    ]

    assert not offending, (
        "SECURITY.md contains text that mentions both a vulnerability and an issue without "
        f"negating an instruction to file one -- this reads as steering a reporter toward a "
        f"public issue instead of the private channel: {offending!r}"
    )
