"""Synthetic validation of the shared `uv sync` command scanner (GH-19).

`tests/_uv_sync_command_scan.py` decides what the two `uv sync` guards
(`tests/test_markdown_install_instructions_all_packages.py` and
`tests/test_contribution_governance_docs.py`) are even shown. If the scanner
silently stops recognizing a command shape, both guards go green while
guarding nothing -- which is exactly what happened before this module
existed: both carried their own copy of `r"^\\s*\\$?\\s*uv sync\\b"`, anchored
to the start of a line, so `cd frontend && uv sync` was invisible to both
while their docstrings claimed to cover any runnable `uv sync` command.

The guards themselves only ever exercise the command shapes the repository's
markdown happens to contain today (which is one shape: a bare
`uv sync --all-packages` alone on its line). These cases pin the scanner's
behaviour against the shapes it must find, the shapes it must ignore, and
the near-misses in between -- independently of what any document looks like
at any moment.
"""

from __future__ import annotations

import pytest
from _uv_sync_command_scan import command_tokens, find_uv_sync_commands

ALL_PACKAGES_FLAG = "--all-packages"

# Synthetic markdown documents, one per command shape the scanner must
# classify. Fenced blocks stand in for the copy-pasteable setup sections real
# documents use; unfenced lines stand in for prose and Markdown tables.
_SCANNER_CASES: dict[str, str] = {
    # --- shapes that must be found -------------------------------------
    "bare_command_alone_in_a_fence": "```bash\nuv sync\n```\n",
    "flagged_command_alone_in_a_fence": "```bash\nuv sync --all-packages\n```\n",
    "command_at_line_start_outside_any_fence": "uv sync --all-packages\n",
    "indented_command_in_a_fence": "```bash\n    uv sync\n```\n",
    "prompt_prefixed_command_in_a_fence": "```console\n$ uv sync --all-packages\n```\n",
    "and_chained_command_in_a_fence": "```bash\ncd 1komma5 && uv sync\n```\n",
    "semicolon_chained_command_in_a_fence": "```bash\ncd 1komma5; uv sync\n```\n",
    "piped_command_in_a_fence": "```bash\ncat requirements.txt | uv sync\n```\n",
    "or_chained_command_in_a_fence": "```bash\nfalse || uv sync\n```\n",
    "chained_command_keeps_its_own_flag": "```bash\ncd 1komma5 && uv sync --all-packages\n```\n",
    "tilde_fence_is_scanned_like_a_backtick_fence": "~~~bash\ncd 1komma5 && uv sync\n~~~\n",
    # A second invocation must be reported separately from the first, or a
    # bare `uv sync` could hide behind a flagged one on the same line.
    "two_invocations_on_one_line_are_reported_separately": (
        "```bash\nuv sync --all-packages && uv sync\n```\n"
    ),
    # --- shapes that must be ignored -----------------------------------
    # Prose. The mention sits mid-sentence and is wrapped in backticks, so it
    # starts neither a line nor a segment.
    "prose_mention_is_not_a_command": "Run `uv sync --all-packages` to install everything.\n",
    "prose_mention_of_a_chained_command_is_not_a_command": (
        "Run `cd frontend && uv sync` before anything else.\n"
    ),
    # CONTRIBUTING.md's real shape: a paragraph that opens with an inline-code
    # mention of the bare command in order to warn against it.
    "prose_line_opening_with_an_inline_code_mention_is_not_a_command": (
        "`uv sync` installs only that empty root plus the `dev` dependency group.\n"
    ),
    # A Markdown table's `|` cell separators are not shell pipes. Every
    # markdown file in this repository contains tables; splitting them on `|`
    # outside a fence would manufacture commands nobody wrote.
    "markdown_table_outside_a_fence_is_not_a_pipeline": (
        "| Step | Command |\n|---|---|\n| Install | uv sync |\n"
    ),
    # A prose semicolon is not a command chain.
    "prose_semicolon_outside_a_fence_is_not_a_chain": (
        "This was GH-13; uv sync alone will not do.\n"
    ),
    # `uv` must be its own word: `myuv sync` and `./uv sync` are not it.
    "uv_embedded_in_a_longer_word_is_not_a_command": "```bash\nmyuv sync\n```\n",
    # `uv` alone, or followed by a different subcommand, is not `uv sync`.
    "a_different_uv_subcommand_is_not_a_sync": "```bash\nuv run pytest -q\n```\n",
}

# `(line number, command segment)` for each invocation the scanner must
# report, in document order.
_SCANNER_EXPECTED: dict[str, list[tuple[int, str]]] = {
    "bare_command_alone_in_a_fence": [(2, "uv sync")],
    "flagged_command_alone_in_a_fence": [(2, "uv sync --all-packages")],
    "command_at_line_start_outside_any_fence": [(1, "uv sync --all-packages")],
    "indented_command_in_a_fence": [(2, "uv sync")],
    "prompt_prefixed_command_in_a_fence": [(2, "uv sync --all-packages")],
    "and_chained_command_in_a_fence": [(2, "uv sync")],
    "semicolon_chained_command_in_a_fence": [(2, "uv sync")],
    "piped_command_in_a_fence": [(2, "uv sync")],
    "or_chained_command_in_a_fence": [(2, "uv sync")],
    "chained_command_keeps_its_own_flag": [(2, "uv sync --all-packages")],
    "tilde_fence_is_scanned_like_a_backtick_fence": [(2, "uv sync")],
    "two_invocations_on_one_line_are_reported_separately": [
        (2, "uv sync --all-packages"),
        (2, "uv sync"),
    ],
    "prose_mention_is_not_a_command": [],
    "prose_mention_of_a_chained_command_is_not_a_command": [],
    "prose_line_opening_with_an_inline_code_mention_is_not_a_command": [],
    "markdown_table_outside_a_fence_is_not_a_pipeline": [],
    "prose_semicolon_outside_a_fence_is_not_a_chain": [],
    "uv_embedded_in_a_longer_word_is_not_a_command": [],
    "a_different_uv_subcommand_is_not_a_sync": [],
}


@pytest.mark.parametrize("case_id", sorted(_SCANNER_CASES))
def test_scanner_classifies_synthetic_markdown_documents(case_id: str) -> None:
    """Given a synthetic markdown document covering one `uv sync` command
    shape, when the shared scanner reads it, then it must report exactly the
    expected `(line number, command)` pairs -- so the two guards that depend
    on it are known to see chained commands and known not to see prose."""
    found = find_uv_sync_commands(_SCANNER_CASES[case_id])
    assert [(item.line_number, item.command) for item in found] == _SCANNER_EXPECTED[case_id]


def test_scanner_reports_the_whole_source_line_alongside_the_command() -> None:
    """Given a chained command, when the scanner reports it, then `command`
    must hold only the `uv sync` segment while `line` holds the whole source
    line, so a failure message can show the reader the command in the context
    they actually wrote it in."""
    (found,) = find_uv_sync_commands(_SCANNER_CASES["and_chained_command_in_a_fence"])
    assert found.command == "uv sync"
    assert found.line == "cd 1komma5 && uv sync"


def test_a_separator_inside_a_quoted_string_does_not_split_the_line() -> None:
    """Given README.md's real PowerShell block, whose first line assigns
    `"$env:USERPROFILE\\.local\\bin;$env:Path"` -- a semicolon inside a string
    literal -- when the scanner reads it, then that line must not be torn in
    half and only the genuine `uv sync` on the following line may be
    reported.

    This is why the segment splitter tracks quoting rather than calling
    `str.split(";")`."""
    markdown = (
        "```powershell\n"
        '$env:Path = "$env:USERPROFILE\\.local\\bin;$env:Path"\n'
        "uv sync --all-packages\n"
        "```\n"
    )
    found = find_uv_sync_commands(markdown)
    assert [(item.line_number, item.command) for item in found] == [(3, "uv sync --all-packages")]


def test_a_bare_chained_command_fails_the_all_packages_check() -> None:
    """Given a chained bare `uv sync`, when its tokens are inspected, then
    `--all-packages` must be absent -- the positive half of the guard's
    verdict, proving a chained bare command is actually caught and not merely
    found."""
    (found,) = find_uv_sync_commands(_SCANNER_CASES["and_chained_command_in_a_fence"])
    assert ALL_PACKAGES_FLAG not in command_tokens(found.command)


def test_a_chained_command_with_the_flag_passes_the_all_packages_check() -> None:
    """Given the same chained shape carrying `--all-packages`, when its
    tokens are inspected, then the flag must be present -- the negative
    control for the test above, proving the broadened scan does not condemn
    every chained command it now sees."""
    (found,) = find_uv_sync_commands(_SCANNER_CASES["chained_command_keeps_its_own_flag"])
    assert ALL_PACKAGES_FLAG in command_tokens(found.command)


def test_a_second_bare_invocation_cannot_borrow_the_first_ones_flag() -> None:
    """Given `uv sync --all-packages && uv sync`, when each reported
    invocation is tokenized separately, then the first must carry the flag
    and the second must not -- proving the guard inspects each invocation's
    own flags rather than searching the whole line, where the bare second
    command would pass on the first one's `--all-packages`."""
    flagged, bare = find_uv_sync_commands(
        _SCANNER_CASES["two_invocations_on_one_line_are_reported_separately"]
    )
    assert ALL_PACKAGES_FLAG in command_tokens(flagged.command)
    assert ALL_PACKAGES_FLAG not in command_tokens(bare.command)


def test_command_tokens_falls_back_when_shlex_refuses_the_command() -> None:
    """Given a `uv sync` command ending in a bare backslash line-continuation
    -- the shape `shlex` rejects with "No escaped character", and one README
    already contains in its `psql` examples -- when its tokens are requested,
    then tokenizing must fall back to a whitespace split rather than raising,
    so an unparsable command is still checked for `--all-packages` instead of
    crashing the guard or slipping past it."""
    assert command_tokens("uv sync --all-packages \\") == [
        "uv",
        "sync",
        "--all-packages",
        "\\",
    ]
