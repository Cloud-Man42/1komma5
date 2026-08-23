"""Tests for the `.github/` contribution-workflow surfaces GH-19 requires
beyond `dependabot.yml` (covered separately in
`tests/test_dependabot_config.py`): `CODEOWNERS`, `pull_request_template.md`,
and the `ISSUE_TEMPLATE/` directory.

This module holds three groups of tests:

1. `CODEOWNERS` (AC2): must exist, contain at least one real ownership
   rule, never reference an unfilled placeholder handle, and actually name
   the repository's real owner (`@L0rdS474n`, verified via `gh api user`
   and `gh repo view` at authoring time -- the account is also the
   repository's sole collaborator). A CODEOWNERS file gates who GitHub
   treats as a required reviewer for matching paths, so a placeholder
   handle here is not cosmetic: it is a broken access-control assignment
   that silently requires review from nobody.
2. `pull_request_template.md` (AC2): must exist and contain at least one
   markdown checklist item, reflecting the Definition-of-Done checklist
   GH-19's proposed remediation calls for.
3. `ISSUE_TEMPLATE/` (AC2, AC6): must exist, contain at least two actual
   templates (excluding GitHub's own `config.yml`, which configures the
   issue chooser rather than being a template itself), and every template
   must parse as either a valid GitHub issue form (YAML) or a valid
   markdown document with YAML frontmatter -- GitHub's two supported issue
   template formats.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GITHUB_DIR = REPO_ROOT / ".github"

CODEOWNERS_PATH = GITHUB_DIR / "CODEOWNERS"
PR_TEMPLATE_PATH = GITHUB_DIR / "pull_request_template.md"
ISSUE_TEMPLATE_DIR = GITHUB_DIR / "ISSUE_TEMPLATE"

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[A-Za-z]{2,}$")

# The repository's actual owner and sole collaborator, per `gh api user`
# and `gh api repos/L0rdS474n/1komma5/collaborators` at authoring time.
EXPECTED_OWNER_HANDLE = "@L0rdS474n"

PLACEHOLDER_OWNER_TOKENS = (
    "@your-username",
    "@your_username",
    "@replace_me",
    "@replace-me",
    "@owner",
    "@example",
    "@octocat",
)

CHECKLIST_ITEM_RE = re.compile(r"^\s*-\s*\[ \]", re.MULTILINE)

# GitHub's special "issue chooser" configuration file. It lives alongside
# issue templates but is not itself a template (its schema is
# `blank_issues_enabled` / `contact_links`, not `name`/`description`/`body`
# or frontmatter), so it is excluded from both the template-count and the
# template-schema checks below.
NON_TEMPLATE_FILENAMES = frozenset({"config.yml", "config.yaml"})
TEMPLATE_SUFFIXES = frozenset({".yml", ".yaml", ".md"})


def _discover_issue_template_files() -> list[Path]:
    """Return every file under `ISSUE_TEMPLATE/` that is itself an issue
    template (not GitHub's `config.yml` chooser configuration), sorted for
    a deterministic parametrization order."""
    if not ISSUE_TEMPLATE_DIR.is_dir():
        return []
    return sorted(
        path
        for path in ISSUE_TEMPLATE_DIR.iterdir()
        if path.is_file()
        and path.name not in NON_TEMPLATE_FILENAMES
        and path.suffix.lower() in TEMPLATE_SUFFIXES
    )


def _parse_github_issue_form_yaml(path: Path) -> None:
    """Assert `path` parses as a valid GitHub issue form: a YAML mapping
    with a non-empty string `name`, a non-empty string `description`, and a
    non-empty `body` list whose elements each declare a string `type`."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path} must parse to a YAML mapping (GitHub issue form)."

    name = data.get("name")
    assert isinstance(name, str) and name.strip(), f"{path} is missing a non-empty 'name'."

    description = data.get("description")
    assert isinstance(description, str) and description.strip(), (
        f"{path} is missing a non-empty 'description'."
    )

    body = data.get("body")
    assert isinstance(body, list) and body, (
        f"{path} is missing a non-empty 'body' list of form elements."
    )
    for index, element in enumerate(body):
        element_type = element.get("type") if isinstance(element, dict) else None
        assert isinstance(element_type, str) and element_type.strip(), (
            f"{path} body element #{index} is missing a string 'type' "
            "(GitHub issue form element schema)."
        )


def _parse_frontmatter_markdown(path: Path) -> None:
    """Assert `path` is a markdown file that opens with a YAML frontmatter
    block (delimited by `---` lines) declaring a non-empty `name` and a
    non-empty `about` (or `description`), followed by non-empty body
    content -- GitHub's legacy issue template format."""
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines and lines[0].strip() == "---", (
        f"{path} must open with a '---' YAML frontmatter delimiter as its first line."
    )
    try:
        closing_index = lines[1:].index("---") + 1
    except ValueError:
        pytest.fail(f"{path} opens a frontmatter block with '---' but never closes it.")

    frontmatter = yaml.safe_load("\n".join(lines[1:closing_index]))
    assert isinstance(frontmatter, dict), f"{path} frontmatter must parse to a YAML mapping."

    name = frontmatter.get("name")
    assert isinstance(name, str) and name.strip(), (
        f"{path} frontmatter is missing a non-empty 'name'."
    )

    about_or_description = frontmatter.get("about") or frontmatter.get("description")
    assert isinstance(about_or_description, str) and about_or_description.strip(), (
        f"{path} frontmatter is missing a non-empty 'about' (or 'description')."
    )

    body_text = "\n".join(lines[closing_index + 1 :]).strip()
    assert body_text, f"{path} has no body content after its frontmatter block."


def test_codeowners_file_exists_and_is_non_empty() -> None:
    """Given `.github/`, when looking for `CODEOWNERS`, then it must exist
    and contain more than whitespace."""
    assert CODEOWNERS_PATH.is_file(), f"Expected {CODEOWNERS_PATH} to exist."
    assert CODEOWNERS_PATH.read_text(encoding="utf-8").strip() != "", (
        f"{CODEOWNERS_PATH} exists but is empty (or only whitespace)."
    )


def test_codeowners_has_at_least_one_well_formed_ownership_rule() -> None:
    """Given `CODEOWNERS`, when its non-comment, non-blank lines are read,
    then each must be a `<pattern> <owner> [<owner> ...]` rule whose owners
    are each either a `@handle`/`@org/team` or an email address, so GitHub
    can actually resolve required reviewers from it instead of silently
    ignoring a malformed line."""
    content = CODEOWNERS_PATH.read_text(encoding="utf-8")
    rule_lines = [
        line for line in content.splitlines() if line.strip() and not line.strip().startswith("#")
    ]
    assert rule_lines, f"Expected at least one non-comment ownership rule in {CODEOWNERS_PATH}."

    for line in rule_lines:
        parts = line.split()
        assert len(parts) >= 2, f"Malformed CODEOWNERS rule (missing an owner): {line!r}"
        owners = parts[1:]
        for owner in owners:
            is_handle = owner.startswith("@") and len(owner) > 1
            is_email = bool(EMAIL_RE.match(owner))
            assert is_handle or is_email, (
                f"Owner {owner!r} on CODEOWNERS line {line!r} is neither a '@handle'/'@org/team' "
                "nor an email address."
            )


def test_codeowners_does_not_reference_a_placeholder_owner() -> None:
    """Given `CODEOWNERS`, when its content is read, then it must not
    contain an unfilled placeholder handle (e.g. `@your-username`,
    `@octocat`) -- a placeholder owner is strictly worse than no CODEOWNERS
    file at all, because it looks like it assigns required reviewers but
    resolves to nobody."""
    content_lower = CODEOWNERS_PATH.read_text(encoding="utf-8").lower()
    for token in PLACEHOLDER_OWNER_TOKENS:
        assert token not in content_lower, (
            f"{CODEOWNERS_PATH} contains the placeholder owner token {token!r}; it must be "
            "replaced with a real GitHub handle or team."
        )


def test_codeowners_references_the_repositorys_actual_owner() -> None:
    """Given `CODEOWNERS`, when its content is read, then it must reference
    the repository's real owner (`@L0rdS474n`), so ownership rules resolve
    to an account that can actually review, rather than to an owner that
    was never updated for this fork."""
    content = CODEOWNERS_PATH.read_text(encoding="utf-8")
    assert EXPECTED_OWNER_HANDLE in content, (
        f"Expected {CODEOWNERS_PATH} to reference {EXPECTED_OWNER_HANDLE!r} "
        "(the repository's actual owner); it was not found."
    )


def test_pull_request_template_exists_and_is_non_empty() -> None:
    """Given `.github/`, when looking for `pull_request_template.md`, then
    it must exist and contain more than whitespace."""
    assert PR_TEMPLATE_PATH.is_file(), f"Expected {PR_TEMPLATE_PATH} to exist."
    assert PR_TEMPLATE_PATH.read_text(encoding="utf-8").strip() != "", (
        f"{PR_TEMPLATE_PATH} exists but is empty (or only whitespace)."
    )


def test_pull_request_template_contains_a_checklist() -> None:
    """Given `pull_request_template.md`, when its content is read, then it
    must contain at least one markdown checklist item (`- [ ]`), reflecting
    the Definition-of-Done checklist GH-19's proposed remediation calls
    for, rather than being free-form prose a reviewer has to interpret."""
    content = PR_TEMPLATE_PATH.read_text(encoding="utf-8")
    assert CHECKLIST_ITEM_RE.search(content), (
        f"Expected {PR_TEMPLATE_PATH} to contain at least one markdown checklist item "
        "('- [ ]'); found none."
    )


def test_issue_template_directory_exists() -> None:
    """Given `.github/`, when looking for `ISSUE_TEMPLATE/`, then it must
    exist as a directory."""
    assert ISSUE_TEMPLATE_DIR.is_dir(), f"Expected {ISSUE_TEMPLATE_DIR} to exist as a directory."


def test_issue_template_directory_has_at_least_two_templates() -> None:
    """Given `ISSUE_TEMPLATE/`, when its contents are listed, then at least
    two actual templates (excluding GitHub's `config.yml` chooser
    configuration) must be present -- GH-19 calls for bug report and
    feature request templates at minimum."""
    templates = _discover_issue_template_files()
    assert len(templates) >= 2, (
        f"Expected at least 2 issue templates under {ISSUE_TEMPLATE_DIR} "
        f"(excluding config.yml); found {[p.name for p in templates]}."
    )


@pytest.mark.parametrize(
    "template_path",
    _discover_issue_template_files(),
    ids=lambda p: p.name,
)
def test_issue_template_parses_as_valid_github_form_or_frontmatter_markdown(
    template_path: Path,
) -> None:
    """Given a file under `ISSUE_TEMPLATE/` (other than `config.yml`), when
    it is parsed, then it must be valid according to whichever of GitHub's
    two supported issue template formats its extension implies: a YAML
    issue form (`.yml`/`.yaml`) or a markdown document with YAML
    frontmatter (`.md`). A template that fails to parse renders as broken
    (or not at all) in GitHub's issue chooser."""
    suffix = template_path.suffix.lower()
    if suffix in {".yml", ".yaml"}:
        _parse_github_issue_form_yaml(template_path)
    elif suffix == ".md":
        _parse_frontmatter_markdown(template_path)
    else:  # pragma: no cover - excluded by TEMPLATE_SUFFIXES, kept as a defensive guard
        pytest.fail(f"Unexpected issue template file extension for {template_path}: {suffix!r}")
