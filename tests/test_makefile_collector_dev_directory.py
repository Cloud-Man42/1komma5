"""Tests for `uv` flag placement in every `uv run` command this repository
ships -- both the Makefile's `run` recipes and the copy-pasteable commands in
`README.md` (GH-14).

`Makefile:25-26` reads::

    collector-dev:
        $(UV) run python -m app --directory collector

`uv run` treats everything from the invoked command's name onward as that
command's own argv, not as options for `uv` itself. `--directory` is a
global `uv` option (it tells `uv` which directory to run *in*, before it
even starts the child process), so it must appear before the command name
`uv run` is about to execute -- either before `run` itself
(`uv --directory collector run python -m app`) or between `run` and the
command name (`uv run --directory collector python -m app`). Placed after
the command name, as it is on `Makefile:26`, it is not consumed by `uv` at
all: it is forwarded verbatim into the child process's own argv, which for
`python -m app --directory collector` means `app.collector`'s entry point
sees `--directory collector` as its own (unrecognized) arguments while `uv`
runs it from whatever directory `make` was invoked in -- not from
`collector/`.

Both accepted placements were verified empirically against this
repository's `collector/` package before writing these tests:

    $ uv --directory collector run python -c "import os; print(os.getcwd())"
    .../collector
    $ uv run --directory collector python -c "import os; print(os.getcwd())"
    .../collector
    $ uv run python -c "import os, sys; print(os.getcwd()); print(sys.argv)" --directory collector
    <repo root, not collector/>
    ['-c', '--directory', 'collector']

`test_collector_dev_recipe_places_directory_flag_before_the_command_it_configures`
inspects `collector-dev`'s recipe tokens directly for this ordering (AC1).
`test_collector_dev_working_directory_is_the_collector_package` exercises the
*effect* of that ordering: it runs `collector-dev`'s recipe exactly as
`make` executes it, with `python -m app` (which would start a long-running
service) swapped for a `python -c` probe that reports its own working
directory and exits immediately, keeping every other token -- including
wherever `--directory collector` currently sits -- untouched (AC2).
`test_no_makefile_recipe_places_a_uv_flag_after_the_command_it_configures`
generalizes the same flag-position check to every `$(UV) run` recipe in the
Makefile, so a future recipe cannot reintroduce this bug under a different
target name (AC3). It is parametrized to include `backend-dev`
(`Makefile:22-23`), whose `--app-dir` is uvicorn's own flag, not one of
`uv`'s -- proving the guard does not flag it as a false positive.

`README.md`'s "Windows equivalents (without make)" section spells the same
commands out longhand for readers who run them without `make`, and it carried
the identical misordering (`uv run python -m app --directory collector`) after
the Makefile was fixed. A reader who copies that line hits exactly the bug
GH-14 closes, so
`test_readme_uv_commands_place_uv_flags_before_the_command_they_configure`
applies the same flag-position rule to every `uv run` command in README's
fenced code blocks, and
`test_readme_collector_command_matches_the_makefile_collector_dev_recipe`
pins README's collector command to the Makefile recipe token-for-token so the
two cannot drift apart again.

Both scans -- the Makefile one and the README one -- are cross-checked against
an independent raw-text scan
(`test_uv_run_recipe_scan_matches_an_independent_makefile_text_scan`,
`test_readme_uv_run_line_scan_matches_an_independent_text_scan`) so that a
`uv run` command written in a shape the structured parser does not recognize
fails loudly instead of silently dropping out of the parametrized guards and
leaving them reporting "no failures" for something they never looked at.

This module's file name predates its README coverage; see the note on
`README_PATH` below.
"""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import NamedTuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE_PATH = REPO_ROOT / "Makefile"
MAKEFILE_TEXT = MAKEFILE_PATH.read_text(encoding="utf-8")
COLLECTOR_DIR = REPO_ROOT / "collector"

# This module is named for the Makefile because that is where GH-14's bug
# lived, but the same bug is reintroducible from README's copy-pasteable
# commands, so README is guarded here too rather than from a second module
# that would have to duplicate the detector below. The file name is
# consequently narrower than its contents; renaming it to something like
# `test_uv_flag_placement.py` is worth doing, but as its own change so the
# rename is reviewable separately from the guard it would be moving.
README_PATH = REPO_ROOT / "README.md"
README_TEXT = README_PATH.read_text(encoding="utf-8")

_MAKE_BINARY = shutil.which("make")
_UV_BINARY = shutil.which("uv")

# `uv`'s own global options that configure how `uv` itself behaves (which
# directory/project it operates on, which interpreter it selects, whether it
# is allowed to touch the lockfile/environment) as opposed to options meant
# for the command `uv run` invokes. Each of these must precede the command
# name `uv run` is about to execute. This list intentionally does NOT
# include flags like uvicorn's `--app-dir` (Makefile:23): those belong to the
# invoked command, not to uv, and are correctly placed after the command
# name.
KNOWN_UV_FLAGS = frozenset(
    {"--directory", "--project", "--python", "--frozen", "--locked", "--no-sync"}
)
# Subset of KNOWN_UV_FLAGS that consumes a following token as its value
# (e.g. `--directory collector`), as opposed to a bare boolean switch
# (e.g. `--frozen`).
UV_FLAGS_WITH_VALUE = frozenset({"--directory", "--project", "--python"})

# How `uv` itself is spelled at the start of a command line, depending on
# where that command line is written: the Makefile invokes it through its
# `UV ?= uv` variable (`Makefile:1`), README spells it literally. Anything
# else (`uvx`, `./uv-wrapper`) is a different program and is deliberately not
# matched -- this guard only claims to reason about `uv run`'s own option
# parsing.
UV_PROGRAM_TOKENS = frozenset({"$(UV)", "uv"})

# Matches a Makefile target definition line (`name:` optionally followed by
# prerequisites), excluding `:=`-style variable assignments, which also
# contain a colon but are not target definitions.
_TARGET_RE = re.compile(r"^([A-Za-z0-9_.-]+):(?!=)")


def _parse_recipes(makefile_text: str) -> dict[str, list[str]]:
    """Parse `makefile_text` into a mapping of target name to its recipe
    lines (tab-indented lines following that target's definition, with the
    leading tab stripped). Blank lines, comments, and variable assignments
    end the current target's recipe block, matching GNU Make's own rule
    that a recipe line must immediately follow its target (or a previous
    recipe line of the same target)."""
    recipes: dict[str, list[str]] = {}
    current: str | None = None
    for line in makefile_text.splitlines():
        if line.startswith("\t"):
            if current is not None:
                recipes.setdefault(current, []).append(line[1:])
            continue
        match = _TARGET_RE.match(line)
        current = match.group(1) if match else None
    return recipes


def _uv_command_boundary(tokens_after_run: list[str]) -> int:
    """Given the tokens that follow `run` in a `$(UV) run ...` recipe line,
    return the index of the first token that is the command `uv run` will
    actually execute (e.g. `python`, `uvicorn`) -- i.e. the first token that
    is not one of `uv`'s own recognized global flags, nor a value consumed
    by one of them. Returns `len(tokens_after_run)` if every token is a
    recognized uv flag (or its value) and no command name is present."""
    i = 0
    while i < len(tokens_after_run):
        token = tokens_after_run[i]
        if token in UV_FLAGS_WITH_VALUE:
            i += 2
            continue
        if token in KNOWN_UV_FLAGS:
            i += 1
            continue
        return i
    return len(tokens_after_run)


def _find_misplaced_uv_flags(command_line: str) -> list[str]:
    """Return the known uv flags in `command_line` that are positioned at or
    after the command name `uv run` invokes -- i.e. flags that will be
    forwarded into the invoked command's own argv instead of being consumed
    by `uv`. Returns an empty list if `command_line` does not invoke
    `uv run <command>` (spelled either `$(UV)` as in the Makefile or `uv` as
    in README, per `UV_PROGRAM_TOKENS`), or if every uv flag present precedes
    the command name."""
    tokens = shlex.split(command_line)
    if not tokens or tokens[0] not in UV_PROGRAM_TOKENS or "run" not in tokens:
        return []
    run_index = tokens.index("run")
    tokens_after_run = tokens[run_index + 1 :]
    boundary = _uv_command_boundary(tokens_after_run)
    command_and_after = tokens_after_run[boundary:]
    return [token for token in command_and_after if token in KNOWN_UV_FLAGS]


def _run_probe_target(
    tmp_path: Path, target: str, recipe_command: str
) -> subprocess.CompletedProcess[str]:
    """Define `target` as a Make target with a single recipe line running
    `recipe_command`, in a throwaway wrapper Makefile that `include`s the
    real repository Makefile, then run `make <target>` from `REPO_ROOT` and
    return the result.

    `include`-ing the real Makefile (rather than copying or re-parsing it)
    means `$(UV)` resolves exactly as it does for `make collector-dev`.
    Running the probe via `-C REPO_ROOT` matches the working directory
    `make` starts every recipe's subshell from, so the reported working
    directory reflects exactly what `make collector-dev`'s own recipe would
    see -- not an artifact of where this test happens to run from.
    """
    wrapper_path = tmp_path / "probe.mk"
    wrapper_path.write_text(
        f"include {MAKEFILE_PATH}\n\n.PHONY: {target}\n{target}:\n\t{recipe_command}\n",
        encoding="utf-8",
    )

    return subprocess.run(
        ["make", "--no-print-directory", "-f", str(wrapper_path), "-C", str(REPO_ROOT), target],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_collector_dev_recipe_places_directory_flag_before_the_command_it_configures() -> None:
    """Given `Makefile:25-26`'s `collector-dev` recipe, when its command
    tokens are inspected, then `--directory` must not be positioned at or
    after the command name (`python`) it is meant to configure -- it must
    precede that command name, either before `run` or immediately after
    `run`. `--directory` positioned after the command name is silently
    forwarded to that command's own argv instead of being consumed by
    `uv`."""
    recipes = _parse_recipes(MAKEFILE_TEXT)
    collector_dev_lines = recipes.get("collector-dev")
    assert collector_dev_lines, (
        f"{MAKEFILE_PATH} has no `collector-dev` recipe; update this test if the target was "
        "renamed."
    )

    misplaced = [
        flag
        for line in collector_dev_lines
        for flag in _find_misplaced_uv_flags(line)
        if flag == "--directory"
    ]
    assert misplaced == [], (
        "`collector-dev`'s recipe places `--directory` after the command name it is meant to "
        f"configure: {collector_dev_lines!r}. `uv run` only treats options before the command "
        "name as its own; anything after is forwarded to the command's argv untouched, so "
        "`--directory collector` never changes uv's working directory. Move `--directory "
        "collector` to precede the command name, either before `run` "
        "(`$(UV) --directory collector run ...`) or immediately after it "
        "(`$(UV) run --directory collector ...`)."
    )


def test_collector_dev_working_directory_is_the_collector_package(tmp_path: Path) -> None:
    """Given `collector-dev`'s recipe exactly as written in the Makefile,
    when it is executed the way `make` executes it (via `make -C
    <repo root> collector-dev`), then the recipe's working directory must be
    `collector/`. The recipe's `python -m app` invocation is replaced with a
    `python -c` probe that prints its own working directory and exits
    immediately -- so this test exercises the real, unmodified flag
    placement from the Makefile without starting the long-running collector
    service `python -m app` would start."""
    if _MAKE_BINARY is None:
        pytest.skip("make is not on PATH; cannot exercise the Makefile's recipe environment.")
    if _UV_BINARY is None:
        pytest.skip("uv is not on PATH; cannot exercise a uv-running Makefile recipe.")

    recipes = _parse_recipes(MAKEFILE_TEXT)
    collector_dev_lines = recipes.get("collector-dev")
    assert collector_dev_lines and len(collector_dev_lines) == 1, (
        f"expected `collector-dev` to have exactly one recipe line, found {collector_dev_lines!r}"
        f" in {MAKEFILE_PATH}; update this test if the recipe's shape changed."
    )
    original_line = collector_dev_lines[0]

    marker = "COLLECTOR_DEV_CWD"
    substituted = original_line.replace(
        "python -m app",
        f"python -c \"import os; print('{marker}=' + os.getcwd())\"",
    )
    assert substituted != original_line, (
        f"expected the substring 'python -m app' in collector-dev's recipe {original_line!r}; "
        "update this test's substitution if the recipe's command changed."
    )
    # Prefixed with `@` so `make` does not echo the command line before running
    # it. Without this, the echoed line -- which contains the marker text as
    # part of the quoted `python -c` source it's about to run -- would appear
    # in stdout *before* the marker's real, printed occurrence, and a naive
    # search would match that echoed (wrong) occurrence instead.
    probe_command = f"@{substituted}"

    probe = _run_probe_target(tmp_path, "_collector_dev_cwd_probe", probe_command)
    assert probe.returncode == 0, (
        f"`make collector-dev`'s recipe (with `python -m app` swapped for a `python -c` cwd "
        f"probe) exited with {probe.returncode} instead of starting a short-lived process.\n"
        f"--- stdout ---\n{probe.stdout}\n--- stderr ---\n{probe.stderr}"
    )

    match = re.search(rf"^{marker}=(.+)$", probe.stdout, re.MULTILINE)
    assert match, (
        f"the `collector-dev` cwd probe did not print the expected "
        f"'{marker}=<path>' marker.\n--- stdout ---\n{probe.stdout}\n--- stderr ---\n"
        f"{probe.stderr}"
    )

    reported_cwd = Path(match.group(1).strip())
    assert reported_cwd == COLLECTOR_DIR.resolve(), (
        f"`make collector-dev`'s recipe, run exactly as written (only `python -m app` replaced "
        f"by a `python -c` probe that reports its own cwd and exits, every other token -- "
        f"including wherever `--directory collector` sits -- left untouched), reported working "
        f"directory {reported_cwd}, but it must be {COLLECTOR_DIR.resolve()}. `uv run` only "
        "honors `--directory` when it precedes the command name it invokes; placed after the "
        "command name it is forwarded to that command's own argv and never changes uv's "
        "working directory, so the recipe runs from wherever `make` itself was invoked instead "
        "of from collector/."
    )


def _uv_run_targets(makefile_text: str) -> list[tuple[str, str]]:
    """Return `(target, recipe_line)` pairs for every recipe line, across
    every target in `makefile_text`, that invokes `$(UV) run <command>`.
    Targets with recipes that don't invoke `uv run` at all (e.g.
    `frontend-dev`, `docker-build`) are excluded, since the "flag before
    the command name" property this module tests only applies to lines
    that actually invoke a command via `uv run`."""
    pairs: list[tuple[str, str]] = []
    for target, lines in _parse_recipes(makefile_text).items():
        for line in lines:
            tokens = shlex.split(line)
            if tokens[:1] == ["$(UV)"] and "run" in tokens:
                pairs.append((target, line))
    return pairs


_UV_RUN_TARGET_CASES = _uv_run_targets(MAKEFILE_TEXT)


@pytest.mark.parametrize(
    "target, recipe_line",
    _UV_RUN_TARGET_CASES,
    ids=[target for target, _ in _UV_RUN_TARGET_CASES],
)
def test_no_makefile_recipe_places_a_uv_flag_after_the_command_it_configures(
    target: str, recipe_line: str
) -> None:
    """Given every `$(UV) run <command>` recipe line in the Makefile, when
    the tokens after `run` are inspected, then none of uv's own flags
    (`--directory`, `--project`, `--python`, `--frozen`, `--locked`,
    `--no-sync`) may appear at or after the invoked command's name --
    that position forwards them into the command's own argv instead of
    letting `uv` consume them. This includes `backend-dev`
    (`Makefile:22-23`), whose `--app-dir` is uvicorn's own flag rather than
    one of uv's and must not be flagged by this guard."""
    misplaced = _find_misplaced_uv_flags(recipe_line)
    assert misplaced == [], (
        f"target `{target}`'s recipe {recipe_line!r} places uv flag(s) {misplaced!r} after the "
        "command name uv invokes, so uv never consumes them and forwards them into that "
        "command's own argv instead. Move them to precede the command name."
    )


def test_uv_run_target_cases_cover_collector_dev_and_backend_dev() -> None:
    """Given the Makefile as it stands today, when the set of `$(UV) run
    ...` recipes is collected for the parametrized guard above, then it
    must include both `collector-dev` (the target GH-14 is about) and
    `backend-dev` (the target whose `--app-dir` must NOT be flagged as a
    false positive). This documents, and locks in, that the parametrized
    guard's coverage is not accidentally empty or missing either target --
    a parametrized test with zero cases would silently report "no
    failures" without checking anything."""
    covered_targets = {target for target, _ in _UV_RUN_TARGET_CASES}
    assert {"collector-dev", "backend-dev"}.issubset(covered_targets), (
        f"expected the `$(UV) run` recipe scan to cover both 'collector-dev' and 'backend-dev', "
        f"found: {sorted(covered_targets)}"
    )


# Deliberately independent of `_parse_recipes`/`_uv_run_targets`: a plain text
# scan for `$(UV) run` on tab-indented (i.e. recipe) lines. Its only job is to
# disagree with the structured scan whenever the structured scan misses
# something, so it must not share the structured scan's parsing assumptions.
_RAW_MAKEFILE_UV_RUN_RE = re.compile(r"\$\(UV\)\s+run\b")


def _raw_makefile_uv_run_lines(makefile_text: str) -> set[str]:
    """Return every tab-indented (recipe) line in `makefile_text` that
    mentions `$(UV) run` anywhere on it, stripped, found by plain text search
    rather than by parsing targets and tokenizing recipes."""
    return {
        line.strip()
        for line in makefile_text.splitlines()
        if line.startswith("\t") and _RAW_MAKEFILE_UV_RUN_RE.search(line)
    }


def test_uv_run_recipe_scan_matches_an_independent_makefile_text_scan() -> None:
    """Given the Makefile, when the structured scan that feeds the
    parametrized guard (`_uv_run_targets`, which parses targets and requires
    `$(UV)` to be the recipe line's *first* token) is compared against an
    independent plain-text scan for `$(UV) run` on any recipe line, then the
    two must find exactly the same lines.

    `test_uv_run_target_cases_cover_collector_dev_and_backend_dev` only pins
    the two targets that exist today; a third `$(UV) run` recipe written in a
    shape the structured parser does not recognize -- `cd x && $(UV) run ...`,
    a recipe line prefixed with `@` or `-`, a target name the target regex
    rejects -- would drop out of the parametrization silently, and a
    parametrized guard with a missing case reports no failure for the line it
    never saw. This test makes that drop loud."""
    structured = {line.strip() for _, line in _UV_RUN_TARGET_CASES}
    raw = _raw_makefile_uv_run_lines(MAKEFILE_TEXT)
    assert structured == raw, (
        "the structured `$(UV) run` recipe scan and an independent text scan of "
        f"{MAKEFILE_PATH} disagree, so the parametrized flag-position guard is not actually "
        f"covering every `$(UV) run` recipe line.\nOnly the text scan found (these are NOT "
        f"being checked): {sorted(raw - structured)}\nOnly the structured scan found: "
        f"{sorted(structured - raw)}\nTeach `_uv_run_targets` the recipe shape it is missing, "
        "or adjust the text scan if the Makefile's conventions changed."
    )


# --- README's copy-pasteable `uv run` commands -----------------------------
#
# README's "Windows equivalents (without make)" section restates the Makefile's
# dev commands longhand. A reader copies those lines verbatim, so a misordered
# uv flag there is the same bug as in the Makefile -- just with no build step
# to catch it.

# Matches an opening or closing fenced-code-block delimiter. Up to three
# leading spaces are allowed, per CommonMark.
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")

# Deliberately independent of `shlex`: a plain text scan for `uv run`, used
# only to disagree with the tokenizer-based scan when that scan misses a
# command. The negative lookbehind keeps it from matching `uv` embedded in a
# longer word or path (`./myuv run`, `nouv run`).
_RAW_MARKDOWN_UV_RUN_RE = re.compile(r"(?<![\w.$/-])uv\s+run\b")


class _MarkdownUvScan(NamedTuple):
    """`uv_run_lines`: `(line number, line)` for each fenced-code-block line
    that tokenizes as a `uv run <command>` invocation. `unparsable_lines`:
    `(line number, line)` for each fenced-code-block line `shlex` refused to
    tokenize (README really does contain such lines -- the `psql` examples end
    in a bare backslash line-continuation). Unparsable lines are recorded
    rather than discarded so that
    `test_readme_uv_run_line_scan_matches_an_independent_text_scan` can name
    them if a `uv run` command ever hides in one."""

    uv_run_lines: list[tuple[int, str]]
    unparsable_lines: list[tuple[int, str]]


def _fenced_code_block_lines(markdown_text: str) -> list[tuple[int, str]]:
    """Return `(line number, line)` for every line of `markdown_text` that
    sits inside a fenced code block, excluding the fence delimiters
    themselves. Restricting the scan to code blocks is what keeps README's
    prose and its Markdown tables (whose `|` cell separators would otherwise
    look like shell pipes) out of the shell tokenizer."""
    inside: list[tuple[int, str]] = []
    fence_char: str | None = None
    for number, line in enumerate(markdown_text.splitlines(), start=1):
        match = _FENCE_RE.match(line)
        if fence_char is None:
            if match:
                fence_char = match.group(1)[0]
            continue
        if match and match.group(1)[0] == fence_char:
            fence_char = None
            continue
        inside.append((number, line))
    return inside


def _scan_markdown_uv_run_commands(markdown_text: str) -> _MarkdownUvScan:
    """Scan `markdown_text`'s fenced code blocks for `uv run <command>`
    invocations.

    A line counts as a uv invocation when its first shell token is one of
    `UV_PROGRAM_TOKENS` and `run` is among its tokens. Commands that are not
    the first thing on their line (`cd x && uv run ...`) are therefore not
    recognized; that blind spot is deliberate -- splitting shell lines on
    separators would corrupt README's quoted PowerShell assignment on
    `README.md:108`, whose `;` sits inside a string literal -- and it is
    covered by the independent text scan rather than by a fuller shell
    parser."""
    uv_run_lines: list[tuple[int, str]] = []
    unparsable_lines: list[tuple[int, str]] = []
    for number, line in _fenced_code_block_lines(markdown_text):
        try:
            tokens = shlex.split(line)
        except ValueError:
            unparsable_lines.append((number, line))
            continue
        if tokens and tokens[0] in UV_PROGRAM_TOKENS and "run" in tokens:
            uv_run_lines.append((number, line))
    return _MarkdownUvScan(uv_run_lines, unparsable_lines)


_README_UV_SCAN = _scan_markdown_uv_run_commands(README_TEXT)
_README_UV_RUN_CASES = _README_UV_SCAN.uv_run_lines


@pytest.mark.parametrize(
    "line_number, command_line",
    _README_UV_RUN_CASES,
    ids=[f"README.md-L{number}" for number, _ in _README_UV_RUN_CASES],
)
def test_readme_uv_commands_place_uv_flags_before_the_command_they_configure(
    line_number: int, command_line: str
) -> None:
    """Given every `uv run <command>` line in README's fenced code blocks,
    when the tokens after `run` are inspected, then none of uv's own flags
    may appear at or after the invoked command's name -- the same rule the
    Makefile recipes are held to. README's commands are meant to be copied
    and pasted, so a misordered flag there hands the reader exactly the GH-14
    failure the Makefile no longer has. This includes `README.md:115`, whose
    `--app-dir` is uvicorn's own flag rather than one of uv's and must not be
    flagged."""
    misplaced = _find_misplaced_uv_flags(command_line)
    assert misplaced == [], (
        f"{README_PATH.name}:{line_number} places uv flag(s) {misplaced!r} after the command "
        f"name uv invokes: {command_line!r}. `uv run` only treats options before the command "
        "name as its own; anything after is forwarded into that command's argv untouched. A "
        "reader copying this line gets the flag silently ignored. Move the flag to precede the "
        "command name, e.g. `uv run --directory collector python -m app`."
    )


def test_readme_uv_run_line_scan_matches_an_independent_text_scan() -> None:
    """Given README, when the tokenizer-based scan that feeds the
    parametrized guard above is compared against an independent plain-text
    scan for `uv run` in the same fenced code blocks, then the two must find
    exactly the same lines, and must find at least one.

    Without this, a `uv run` command written in a shape the tokenizer does
    not recognize -- behind a `&&`, on a line `shlex` cannot parse, in a
    future section of the file -- would drop out of the parametrization
    silently, and a parametrized guard reports no failure for a line it never
    saw. This turns that silent drop into a named failure."""
    scanned = {number for number, _ in _README_UV_RUN_CASES}
    raw = {
        number
        for number, line in _fenced_code_block_lines(README_TEXT)
        if _RAW_MARKDOWN_UV_RUN_RE.search(line)
    }
    assert scanned, (
        f"no `uv run` commands were found in {README_PATH}'s fenced code blocks at all, so the "
        "parametrized README guard is checking nothing. If README genuinely no longer documents "
        "any `uv run` command, delete that guard deliberately rather than leaving it vacuous."
    )
    assert scanned == raw, (
        f"the tokenizer-based `uv run` scan and an independent text scan of {README_PATH} "
        f"disagree, so the parametrized flag-position guard is not covering every documented "
        f"`uv run` command.\nOnly the text scan found (these are NOT being checked): "
        f"{sorted(raw - scanned)}\nOnly the tokenizer found: {sorted(scanned - raw)}\nLines "
        f"shlex could not tokenize: {[number for number, _ in _README_UV_SCAN.unparsable_lines]}"
        "\nTeach `_scan_markdown_uv_run_commands` the command shape it is missing."
    )


def test_readme_collector_command_matches_the_makefile_collector_dev_recipe() -> None:
    """Given README's documented collector command and the Makefile's
    `collector-dev` recipe, when both are tokenized, then everything after
    the `uv` program name must be identical token for token.

    `test_readme_uv_commands_place_uv_flags_before_the_command_they_configure`
    already rejects the specific misordering GH-14 is about; this test is the
    stronger anti-drift claim. README exists to tell a reader what `make
    collector-dev` would have run, so any divergence -- a flag moved, a value
    changed, a module renamed -- is a documentation bug even when both spellings
    happen to be individually valid. The two drifted apart once already: PR #33
    fixed `Makefile:26` and left README's copy carrying the old, broken
    order."""
    readme_collector = [(number, line) for number, line in _README_UV_RUN_CASES if "-m app" in line]
    assert len(readme_collector) == 1, (
        f"expected exactly one `uv run ... -m app` collector command in {README_PATH}, found "
        f"{readme_collector!r}; update this test if README's collector documentation changed "
        "shape."
    )
    line_number, command_line = readme_collector[0]

    collector_dev_lines = _parse_recipes(MAKEFILE_TEXT).get("collector-dev")
    assert collector_dev_lines and len(collector_dev_lines) == 1, (
        f"expected `collector-dev` to have exactly one recipe line, found "
        f"{collector_dev_lines!r} in {MAKEFILE_PATH}; update this test if the recipe's shape "
        "changed."
    )

    # `[1:]` drops the program name only: the Makefile spells it `$(UV)` and
    # README spells it `uv`. Every token after it must match exactly.
    makefile_arguments = shlex.split(collector_dev_lines[0])[1:]
    readme_arguments = shlex.split(command_line)[1:]
    assert readme_arguments == makefile_arguments, (
        f"{README_PATH.name}:{line_number} documents `{command_line}`, but `make collector-dev` "
        f"runs `{collector_dev_lines[0]}`. README's Windows section exists to spell out what the "
        "Makefile target does, so the two must agree token for token after the `uv` program "
        f"name.\nREADME arguments:   {readme_arguments!r}\nMakefile arguments: "
        f"{makefile_arguments!r}"
    )


# --- Synthetic validation of the flag-position detector itself -------------
#
# The tests above run the detector (`_find_misplaced_uv_flags`) against the
# real Makefile, which only ever exercises whichever placement the Makefile
# currently happens to use. The cases below feed the detector synthetic
# recipe lines covering placements the real Makefile does not (yet, or ever)
# contain, so both the "no false negative" and "no false positive" behavior
# of the detector are verified directly, independent of what GH-14's fix
# ends up looking like.
_DETECTOR_CASES: dict[str, str] = {
    "directory_after_run_before_command_is_not_misplaced": (
        "$(UV) run --directory collector python -m app"
    ),
    "directory_before_run_is_not_misplaced": ("$(UV) --directory collector run python -m app"),
    "directory_after_command_name_is_misplaced": ("$(UV) run python -m app --directory collector"),
    "boolean_flag_after_command_name_is_misplaced": ("$(UV) run pytest --frozen"),
    "boolean_flag_before_run_is_not_misplaced": ("$(UV) run --frozen pytest"),
    "non_uv_flag_after_command_name_is_not_misplaced": (
        "$(UV) run uvicorn app.main:app --app-dir backend"
    ),
    "line_without_uv_run_is_ignored": ("cd frontend && npm run dev"),
    "uv_sync_without_run_is_ignored": ("$(UV) sync --all-packages --directory collector"),
    # README spells the program `uv` rather than `$(UV)`; the same placements
    # must classify identically no matter which spelling is used.
    "plain_uv_directory_after_command_name_is_misplaced": (
        "uv run python -m app --directory collector"
    ),
    "plain_uv_directory_before_command_name_is_not_misplaced": (
        "uv run --directory collector python -m app"
    ),
    "plain_uv_directory_before_run_is_not_misplaced": (
        "uv --directory collector run python -m app"
    ),
    "plain_uv_non_uv_flag_after_command_name_is_not_misplaced": (
        "uv run uvicorn app.main:app --app-dir backend"
    ),
    "program_merely_starting_with_uv_is_ignored": ("uvx run python -m app --directory collector"),
}
_DETECTOR_EXPECTED_VIOLATIONS: dict[str, list[str]] = {
    "directory_after_run_before_command_is_not_misplaced": [],
    "directory_before_run_is_not_misplaced": [],
    "directory_after_command_name_is_misplaced": ["--directory"],
    "boolean_flag_after_command_name_is_misplaced": ["--frozen"],
    "boolean_flag_before_run_is_not_misplaced": [],
    "non_uv_flag_after_command_name_is_not_misplaced": [],
    "line_without_uv_run_is_ignored": [],
    "uv_sync_without_run_is_ignored": [],
    "plain_uv_directory_after_command_name_is_misplaced": ["--directory"],
    "plain_uv_directory_before_command_name_is_not_misplaced": [],
    "plain_uv_directory_before_run_is_not_misplaced": [],
    "plain_uv_non_uv_flag_after_command_name_is_not_misplaced": [],
    "program_merely_starting_with_uv_is_ignored": [],
}


@pytest.mark.parametrize("case_id", sorted(_DETECTOR_CASES))
def test_misplaced_uv_flag_detector_classifies_synthetic_recipe_lines_correctly(
    case_id: str,
) -> None:
    """Given synthetic recipe lines covering both accepted uv-flag
    placements (before `run`, and after `run` but before the command
    name), the rejected placement (after the command name), a non-uv flag
    that happens to follow the same pattern as `backend-dev`'s
    `--app-dir`, and lines that don't invoke `uv run` at all, when each is
    passed to the flag-position detector, then it must classify each one
    exactly as expected -- proving the detector used by the tests above
    neither false-positives on a correct or unrelated recipe nor
    false-negatives on a misplaced flag."""
    recipe_line = _DETECTOR_CASES[case_id]
    expected = _DETECTOR_EXPECTED_VIOLATIONS[case_id]
    assert _find_misplaced_uv_flags(recipe_line) == expected


# --- Synthetic validation of the Markdown scanner itself -------------------
#
# The README tests above only ever exercise the command shapes README happens
# to contain today. These cases feed the scanner documents covering the shapes
# it must ignore, the shape it must record as unparsable, and the shape it is
# known not to recognize -- so its behavior is pinned independently of what
# README looks like at any moment.
_MARKDOWN_SCANNER_CASES: dict[str, str] = {
    "uv_run_inside_a_fence_is_found": "```bash\nuv run python -m app\n```\n",
    "uv_run_outside_a_fence_is_ignored": "Run `uv run python -m app` to start it.\n",
    "uv_sync_inside_a_fence_is_ignored": "```bash\nuv sync --all-packages\n```\n",
    # README.md:152's real shape: a trailing backslash line-continuation, which
    # `shlex.split` rejects with "No escaped character".
    "unparsable_line_is_recorded_not_raised": '```bash\npsql -c \\\n  "SELECT 1;"\n```\n',
    # The scanner's documented blind spot; see the negative control below.
    "uv_run_behind_a_shell_separator_is_not_tokenized": (
        "```bash\ncd collector && uv run python -m app --directory .\n```\n"
    ),
    "tables_outside_fences_are_never_tokenized": "| a | b |\n|---|---|\n| uv run x | y |\n",
}
# `(expected uv_run_lines line numbers, expected unparsable_lines line numbers)`
_MARKDOWN_SCANNER_EXPECTED: dict[str, tuple[list[int], list[int]]] = {
    "uv_run_inside_a_fence_is_found": ([2], []),
    "uv_run_outside_a_fence_is_ignored": ([], []),
    "uv_sync_inside_a_fence_is_ignored": ([], []),
    "unparsable_line_is_recorded_not_raised": ([], [2]),
    "uv_run_behind_a_shell_separator_is_not_tokenized": ([], []),
    "tables_outside_fences_are_never_tokenized": ([], []),
}


@pytest.mark.parametrize("case_id", sorted(_MARKDOWN_SCANNER_CASES))
def test_markdown_uv_run_scanner_classifies_synthetic_documents_correctly(case_id: str) -> None:
    """Given synthetic Markdown documents covering a `uv run` command inside
    a fence, the same command in prose outside any fence, a `uv sync` that
    must not be mistaken for a `uv run`, a line `shlex` cannot tokenize, a
    `uv run` behind a shell separator, and a Markdown table whose `|`
    separators must never reach the shell tokenizer, when each is scanned,
    then the scanner must report exactly the expected uv-run and unparsable
    line numbers -- proving it neither crashes on README's real content nor
    silently mis-scopes what the parametrized guard sees."""
    markdown = _MARKDOWN_SCANNER_CASES[case_id]
    expected_uv_lines, expected_unparsable = _MARKDOWN_SCANNER_EXPECTED[case_id]
    scan = _scan_markdown_uv_run_commands(markdown)
    assert [number for number, _ in scan.uv_run_lines] == expected_uv_lines
    assert [number for number, _ in scan.unparsable_lines] == expected_unparsable


def test_readme_text_scan_catches_a_uv_run_command_the_tokenizer_would_drop() -> None:
    """Given a Markdown document whose `uv run` command sits behind a shell
    separator -- the shape `_scan_markdown_uv_run_commands` documents that it
    does not recognize -- when both scans run over it, then the tokenizer must
    find nothing and the independent text scan must find the line, so the two
    disagree.

    This is the negative control for
    `test_readme_uv_run_line_scan_matches_an_independent_text_scan`: it proves
    that cross-check actually goes red when a `uv run` command escapes the
    parametrized guard, rather than being an equality that can only ever
    hold."""
    markdown = _MARKDOWN_SCANNER_CASES["uv_run_behind_a_shell_separator_is_not_tokenized"]
    scanned = {number for number, _ in _scan_markdown_uv_run_commands(markdown).uv_run_lines}
    raw = {
        number
        for number, line in _fenced_code_block_lines(markdown)
        if _RAW_MARKDOWN_UV_RUN_RE.search(line)
    }
    assert scanned == set()
    assert raw == {2}
    assert scanned != raw


def test_makefile_text_scan_catches_a_uv_run_recipe_the_structured_scan_would_drop() -> None:
    """Given a synthetic Makefile whose `$(UV) run` is not the first token of
    its recipe line, when both scans run over it, then `_uv_run_targets` must
    find nothing and the independent text scan must find the recipe line, so
    the two disagree.

    This is the negative control for
    `test_uv_run_recipe_scan_matches_an_independent_makefile_text_scan`,
    proving that cross-check goes red for a recipe the parametrized guard
    would otherwise never be handed."""
    makefile_text = "combined-dev:\n\tcd collector && $(UV) run python -m app\n"
    structured = {line.strip() for _, line in _uv_run_targets(makefile_text)}
    raw = _raw_makefile_uv_run_lines(makefile_text)
    assert structured == set()
    assert raw == {"cd collector && $(UV) run python -m app"}
    assert structured != raw
