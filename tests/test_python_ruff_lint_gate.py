"""Tests for issue #28: `ruff` is configured in the root `pyproject.toml`
but nothing ever invokes it -- neither the Makefile nor CI.

Root `pyproject.toml` declares::

    [tool.ruff]
    line-length = 100
    target-version = "py312"

and `ruff` is a `dependency-groups.dev` entry, so it is installed by
`uv sync --all-packages`. But, measured at authoring time::

    $ grep -rn "ruff" Makefile .github/workflows/*.yml
    (no hits)

    $ uv run ruff check .
    Found 304 errors. [*] 185 fixable with the `--fix` option

    $ uv run ruff format --check .
    140 files would be reformatted, 167 files already formatted

So the configuration exists, but there is no mechanical, non-interactive
way for a contributor, a reviewer, or CI to run it -- the exact same shape
of problem issue #23 was for the frontend (`eslint` configured but never
wired into a runnable gate), which `tests/test_frontend_eslint_lint_gate.py`
covers. This module follows that file's pattern, adapted to what is
different about the Python side.

-- What is deliberately NOT tested here, and why --

Issue #28's own thread (its later comments correct and re-measure the
error/file counts several times as the tree changed underneath them)
explicitly warns against binding an acceptance criterion to a specific
error count or file count. This module follows that: it does not assert
`304`, `185`, `140`, `122`, or any other count anywhere, and it does not
assert that `ruff check`/`ruff format --check` currently pass (they do
not, and deciding how much of the 304 errors to fix, ignore, or exempt --
e.g. the 84 `B008` hits, which are FastAPI's own `Depends()`-in-a-default
-argument idiom, not a real bug -- is Gate 4's decision, not this
module's).

Issue #28 itself also separates *this* concern from wiring the gate into
CI ("#17 är CI-issuen som ska bära det färdiga lint-steget" -- issue #28's
own "Relation till andra issues" section): this module therefore only
requires the gate to be runnable locally and non-interactively (a Makefile
target or a script), and deliberately does not look at
`.github/workflows/*.yml` at all.

Three tests live here, mapped to the issue's two acceptance criteria:

1. `test_a_python_lint_gate_exists_as_a_discoverable_makefile_target_or_script`
   (AC1, and the structural half of AC2): searches the Makefile (including
   targets that only *compose* other targets as prerequisites, e.g.
   `lint: lint-check lint-format`) and `scripts/`/`lint*` files for a
   command sequence that contains both a `ruff check` invocation and a
   `ruff format --check` invocation. Fails today -- there is none. Passes
   once Gate 4 adds one, in whatever shape (single target, split targets
   composed via prerequisites, or a script) Gate 4 chooses; this test does
   not care which.
2. `test_ruff_invocation_classifier_classifies_synthetic_command_lines_correctly`
   (supporting AC1+AC2): a synthetic, dependency-free check that
   `_ruff_invocations_in_line` -- the function the two tests around it rely
   on to tell "a real `ruff check`/`ruff format --check` invocation" apart
   from "a comment, a quoted mention, or a mutating `ruff format` with no
   `--check`" -- classifies a representative set of hand-authored command
   lines correctly, independent of whatever shape the real Makefile/scripts
   happen to be in when this suite runs.
3. `test_gate_exit_code_reflects_the_combined_result_of_ruff_check_and_ruff_format_check`
   (AC2, the core behavioral check): actually runs the discovered gate,
   and separately re-runs -- directly, via `uv run ruff ...` -- the exact
   `ruff` invocations extracted from it, computing what the *correct*
   combined result should be right now (whatever it is: today both real
   invocations fail, so the correct combined result is "fail"; if Gate 4
   leaves a deliberately-tolerated class of errors ignored via
   `pyproject.toml`, the correct combined result changes accordingly, and
   so does what this test expects -- it never hardcodes either outcome).
   It then asserts the gate's own exit code agrees. This is what makes
   AC2's "exit-koden MÅSTE spegla resultatet" a real, checked property
   instead of an assumption: it would fail a gate that always exits 0
   (e.g. `ruff check . || true`), a Makefile recipe line prefixed with `-`
   (Make's ignore-error marker, which would make `make` itself swallow a
   nonzero `ruff` exit rather than propagate it), or a gate that only runs
   one of the two commands while claiming to cover both.

-- Why discovery also resolves prerequisite composition --

This repository's own Makefile already shows the "one target, several
recipe lines" shape for a comparable existing gate (`test:` runs both
`$(UV) run pytest` and `cd frontend && npm test`), so that is one likely
shape for `ruff check` + `ruff format --check` too. But GNU Make's other
idiomatic way to compose two checks under one runnable name is a target
with no recipe of its own that lists both as prerequisites (`lint:
lint-check lint-format`), which is equally valid and arguably more
idiomatic for two independently meaningful checks. Discovery below
resolves prerequisites recursively, so a Gate 4 implementation using
either shape is found.

`.PHONY`-line targets are excluded on purpose from that resolution:
`.PHONY: install migrate seed ...` looks, textually, exactly like a target
definition with those names as its "prerequisites", but running `make
.PHONY` would try to build *every* phony target listed anywhere in the
Makefile in sequence -- including long-running dev servers such as
`backend-dev` -- so `.PHONY` must never be treated as a candidate gate
name. Verified empirically during this module's authoring, before it was
written: a synthetic aggregator target was added to a copy of this
repository's real Makefile text and run through the discovery function
below both with and without excluding dot-prefixed target names; without
the exclusion, `.PHONY` was returned as a spurious second "gate" alongside
the real one. The exclusion below is confirmed necessary, not defensive
overcaution.

-- Why `ruff` invocations are extracted and re-run via `uv run ruff ...`,
not the gate's own wrapper --

The gate might spell the wrapper as `$(UV) run ruff ...` (Makefile),
`uv run ruff ...` (a script), or a bare `ruff ...` relying on an activated
venv. Re-running the extracted `ruff ...` argv through a fixed, known-good
`uv run` wrapper (this repository's own dependency-pinned `ruff`, exactly
as `uv run ruff check .` resolves it everywhere else in this repository)
means the independent "what should the result be" computation does not
depend on knowing, or reproducing, which wrapper spelling the gate itself
used.

-- Why this module can only meaningfully run
`test_gate_exit_code_reflects_the_combined_result_of_ruff_check_and_ruff_format_check`
where `uv` (and, if the discovered gate is a Makefile target, `make`) is on
`PATH` --

Same skip pattern as `tests/test_makefile_pythonpath.py` and
`tests/test_makefile_collector_dev_directory.py`: that test skips, rather
than fails, when a required binary is absent, or when no gate has been
discovered yet (in which case
`test_a_python_lint_gate_exists_as_a_discoverable_makefile_target_or_script`
above is already the one carrying the red signal for that). Discovery
itself and the classifier self-test need no subprocess at all and always
run.

-- Side effects --

`ruff check .` and `ruff format --check .` are both read-only (`--check`
never rewrites files; confirmed via `git status --porcelain` before and
after running both directly during authoring). Neither writes anything
outside the gitignored `.ruff_cache/` (`.gitignore:11`). No `tmp_path`
redirection is needed for that reason. The Makefile-composition scan
itself is a pure text operation on `Makefile`'s own content plus, in the
classifier self-test, hand-authored synthetic strings -- it never writes a
probe Makefile to disk (unlike `tests/test_makefile_pythonpath.py`'s
`_run_probe_target`), since discovery only needs to *read* `Makefile`, not
execute a modified copy of it. Only
`test_gate_exit_code_reflects_the_combined_result_of_ruff_check_and_ruff_format_check`
executes real subprocesses (the discovered gate itself, plus the
independently re-run `ruff` invocations), and it does not modify
`Makefile` to do so.

-- Documented blind spot: `ruff` global flags before the subcommand --

`_ruff_invocations_in_line` classifies a `ruff` invocation by looking at
the token immediately after `ruff` (expecting `check` or `format`). A line
like `ruff --isolated check .`, where a `ruff`-level global flag precedes
the subcommand, is not recognized. This is a deliberate simplification --
no example measured at authoring time (nor this repository's existing
Makefile recipe style) places a flag before the subcommand -- not an
oversight, and
`ruff_global_flag_before_subcommand_is_not_recognized` in the classifier
self-test below pins this blind spot as a named, expected negative rather
than leaving it silently undiscovered.
"""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE_PATH = REPO_ROOT / "Makefile"
MAKEFILE_TEXT = MAKEFILE_PATH.read_text(encoding="utf-8")
SCRIPTS_DIR = REPO_ROOT / "scripts"

_UV_BINARY = shutil.which("uv")
_MAKE_BINARY = shutil.which("make")

# How long the discovered gate (or a single independent `ruff` re-run) is
# allowed to run before this test concludes it is hanging rather than
# merely slow. `ruff check .` and `ruff format --check .` were both
# measured at authoring time to complete in well under a second against
# this repository's full tree, so this is generous headroom, matching the
# 120s bound `tests/test_frontend_eslint_lint_gate.py` and
# `tests/test_frontend_vitest_globals_typecheck.py` use for comparable
# whole-project static-analysis subprocess calls.
GATE_SUBPROCESS_TIMEOUT_SECONDS = 120

# Matches a Makefile target definition line (`name: prereq1 prereq2 ...`),
# excluding `:=`-style variable assignments (which also contain a colon but
# are not target definitions).
_TARGET_DEF_RE = re.compile(r"^([A-Za-z0-9_.-]+):(?!=)\s*(.*)$")

# A shell comment line (including a tab-indented one inside a Makefile
# recipe, or a `#!/usr/bin/env bash` shebang in a script) -- excluded from
# classification so that a `ruff check`/`ruff format --check` mention
# inside a comment is never mistaken for a real invocation.
_COMMENT_LINE_RE = re.compile(r"^\s*#")


# --- Makefile parsing: recipes and prerequisites -----------------------


def _parse_makefile_targets(
    makefile_text: str,
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Parse `makefile_text` into `(recipes, prereqs)`:

    - `recipes[target]`: that target's own tab-indented recipe lines
      (leading tab stripped), matching GNU Make's rule that a recipe line
      must immediately follow its target (or a previous recipe line of the
      same target).
    - `prereqs[target]`: the whitespace-separated tokens written after
      `target:` on its definition line (its prerequisites).

    Dot-prefixed target names (`.PHONY`, `.DEFAULT`, ...) are deliberately
    excluded from both dicts -- see the module docstring's "Why discovery
    also resolves prerequisite composition" section for why treating
    `.PHONY`'s listed names as real prerequisites of a candidate gate would
    be actively dangerous, not merely noisy.
    """
    recipes: dict[str, list[str]] = {}
    prereqs: dict[str, list[str]] = {}
    current: str | None = None
    for line in makefile_text.splitlines():
        if line.startswith("\t"):
            if current is not None:
                recipes.setdefault(current, []).append(line[1:])
            continue
        match = _TARGET_DEF_RE.match(line)
        if match and not match.group(1).startswith("."):
            current = match.group(1)
            prereq_text = match.group(2).strip()
            prereqs[current] = prereq_text.split() if prereq_text else []
        else:
            current = None
    return recipes, prereqs


def _effective_recipe_lines(
    target: str,
    recipes: dict[str, list[str]],
    prereqs: dict[str, list[str]],
    _visited: frozenset[str] = frozenset(),
) -> list[str]:
    """Return `target`'s own recipe lines followed by the effective recipe
    lines of each of its prerequisites, recursively -- i.e. what `make
    <target>` would actually execute, in order, for a target that composes
    other targets purely via prerequisites (no recipe of its own). Guards
    against a prerequisite cycle by never re-expanding a target already on
    the current resolution path."""
    if target in _visited:
        return []
    visited = _visited | {target}
    lines = list(recipes.get(target, []))
    for prereq in prereqs.get(target, []):
        lines.extend(_effective_recipe_lines(prereq, recipes, prereqs, visited))
    return lines


# --- Classifying `ruff` invocations -------------------------------------


def _ruff_invocations_in_line(command_line: str) -> list[tuple[str, list[str]]]:
    """Return `(kind, argv)` for every real `ruff` invocation found in
    `command_line` (there can be more than one if commands are chained,
    e.g. with `&&`): `kind` is `"check"` for a `ruff check ...` invocation
    or `"format-check"` for a `ruff format ... --check ...` invocation
    (the read-only variant used for gating -- plain `ruff format` without
    `--check` mutates files and is a different operation, and is
    deliberately not classified as either). `argv` is the invocation's own
    argv starting at `"ruff"` (e.g. `["ruff", "check", "."]`), suitable for
    re-running directly.

    Tokenizes with `shlex.split`, so a quoted mention (`echo "ruff check
    ."`) never matches: the quoted text becomes a single token, not the
    separate tokens `ruff`/`check`/`.` this function looks for. Lines
    `shlex` cannot tokenize (unbalanced quotes) are treated as containing
    no invocations rather than raising, since a Makefile recipe or script
    line that fails to tokenize as shell is not a `ruff` invocation this
    function can recognize either way.
    """
    try:
        tokens = shlex.split(command_line)
    except ValueError:
        return []
    found: list[tuple[str, list[str]]] = []
    for i, token in enumerate(tokens):
        if token != "ruff" or i + 1 >= len(tokens):
            continue
        rest = tokens[i + 1 :]
        if rest[0] == "check":
            found.append(("check", tokens[i:]))
        elif rest[0] == "format" and "--check" in rest[1:]:
            found.append(("format-check", tokens[i:]))
    return found


def _classify_lines(lines: list[str]) -> list[str]:
    """Return the `kind` (`"check"` / `"format-check"`) of every `ruff`
    invocation found across `lines`, skipping comment lines."""
    kinds: list[str] = []
    for line in lines:
        if _COMMENT_LINE_RE.match(line):
            continue
        kinds.extend(kind for kind, _ in _ruff_invocations_in_line(line))
    return kinds


def _invocations_in_lines(lines: list[str]) -> list[tuple[str, list[str]]]:
    """Return every `(kind, argv)` pair found across `lines`, skipping
    comment lines -- the richer counterpart to `_classify_lines`, used
    where the actual argv (not just its kind) is needed."""
    invocations: list[tuple[str, list[str]]] = []
    for line in lines:
        if _COMMENT_LINE_RE.match(line):
            continue
        invocations.extend(_ruff_invocations_in_line(line))
    return invocations


# --- Discovering the gate -------------------------------------------------


@dataclass(frozen=True)
class DiscoveredGate:
    """`kind`: `"makefile"` or `"script"`. `identifier`: the Makefile
    target name, or the script's path. `lines`: the command lines (own
    recipe plus, for a Makefile target, recursively-resolved prerequisite
    recipes) that were found to cover both a `ruff check` and a `ruff
    format --check` invocation."""

    kind: str
    identifier: str
    lines: list[str]


def _find_makefile_lint_gate() -> DiscoveredGate | None:
    """Search every real (non-dot-prefixed) Makefile target -- including
    ones with no recipe of their own that only compose prerequisites, e.g.
    `lint: lint-check lint-format` -- for one whose effective recipe lines
    cover both a `ruff check` and a `ruff format --check` invocation.
    Returns the first such target found, or `None`."""
    recipes, prereqs = _parse_makefile_targets(MAKEFILE_TEXT)
    for target in sorted(set(recipes) | set(prereqs)):
        lines = _effective_recipe_lines(target, recipes, prereqs)
        kinds = _classify_lines(lines)
        if "check" in kinds and "format-check" in kinds:
            return DiscoveredGate("makefile", target, lines)
    return None


def _candidate_script_paths() -> list[Path]:
    """Every plausible "or a script" location for a Python lint gate:
    every file directly under `scripts/` (this repository's existing
    convention for standalone operational scripts -- `scripts/seed.py`,
    `scripts/stop-local-dev.ps1`, etc.), plus any `lint*`-named file
    directly under the repository root."""
    candidates: list[Path] = []
    if SCRIPTS_DIR.is_dir():
        candidates.extend(path for path in SCRIPTS_DIR.iterdir() if path.is_file())
    candidates.extend(path for path in REPO_ROOT.glob("lint*") if path.is_file())
    return candidates


def _find_script_lint_gate() -> DiscoveredGate | None:
    """Search `_candidate_script_paths()` for a file whose content covers
    both a `ruff check` and a `ruff format --check` invocation. Returns the
    first such file found, or `None`."""
    for path in _candidate_script_paths():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        lines = text.splitlines()
        kinds = _classify_lines(lines)
        if "check" in kinds and "format-check" in kinds:
            return DiscoveredGate("script", str(path), lines)
    return None


def _discover_python_lint_gate() -> DiscoveredGate | None:
    """The Makefile is checked first: this repository's Makefile already
    hosts every comparable existing gate/dev command (`test`, `backend-dev`,
    `collector-dev`, ...), so it is the more likely location. Falls back to
    `_find_script_lint_gate` only if nothing is found there."""
    return _find_makefile_lint_gate() or _find_script_lint_gate()


# --- AC1 (+ structural half of AC2): the gate exists and covers both -------


def test_a_python_lint_gate_exists_as_a_discoverable_makefile_target_or_script() -> None:
    """Given this project, when it is searched for a Python lint gate --
    a Makefile target (including one composed purely of prerequisites) or
    a `scripts/`/`lint*` file -- whose command lines cover both a `ruff
    check` invocation and a `ruff format --check` invocation, then at
    least one must be found. Issue #28 (AC1, and the structural half of
    AC2: "kommandot MÅSTE täcka både `ruff check` och `ruff format
    --check`"). `ruff` is configured in root `pyproject.toml`'s
    `[tool.ruff]`, but, measured at authoring time, nothing in `Makefile`
    or `.github/workflows/*.yml` invokes it at all."""
    gate = _discover_python_lint_gate()
    assert gate is not None, (
        f"no Python lint gate found: no target in {MAKEFILE_PATH} (including targets composed "
        f"purely of prerequisites, e.g. 'lint: lint-check lint-format') and no file under "
        f"{SCRIPTS_DIR} or matching '{REPO_ROOT}/lint*' has command lines covering both a "
        "'ruff check' invocation and a 'ruff format --check' invocation. ruff is configured in "
        "pyproject.toml's [tool.ruff], but nothing invokes it non-interactively (issue #28)."
    )


# --- Classifier self-test: proves the detector both tests above and below
# rely on is correct, independent of whatever shape the real Makefile or
# scripts/ happen to be in when this suite runs. ---------------------------

_CLASSIFIER_CASES: dict[str, str] = {
    "plain_ruff_check_with_path": "ruff check .",
    "uv_wrapped_ruff_check_with_path": "$(UV) run ruff check .",
    "plain_uv_wrapped_ruff_check": "uv run ruff check .",
    "ruff_check_with_extra_flags": "$(UV) run ruff check --no-cache .",
    "ruff_format_check_with_path": "$(UV) run ruff format --check .",
    "ruff_format_check_flag_before_path": "ruff format --check --diff .",
    "ruff_format_without_check_is_not_format_check": "$(UV) run ruff format .",
    "ruff_clean_is_neither_kind": "$(UV) run ruff clean",
    "chained_check_and_format_check_on_one_line": (
        "$(UV) run ruff check . && $(UV) run ruff format --check ."
    ),
    "comment_line_mentioning_ruff_check_is_ignored": "\t# $(UV) run ruff check .",
    "quoted_mention_inside_echo_is_not_a_real_invocation": (
        'echo "ruff check ." && echo "ruff format --check ."'
    ),
    "unrelated_recipe_line_is_ignored": "cd frontend && npm run dev",
    "unparsable_line_is_ignored_not_raised": 'echo "unbalanced quote',
    "ruff_global_flag_before_subcommand_is_not_recognized": "ruff --isolated check .",
}
_CLASSIFIER_EXPECTED: dict[str, list[str]] = {
    "plain_ruff_check_with_path": ["check"],
    "uv_wrapped_ruff_check_with_path": ["check"],
    "plain_uv_wrapped_ruff_check": ["check"],
    "ruff_check_with_extra_flags": ["check"],
    "ruff_format_check_with_path": ["format-check"],
    "ruff_format_check_flag_before_path": ["format-check"],
    "ruff_format_without_check_is_not_format_check": [],
    "ruff_clean_is_neither_kind": [],
    "chained_check_and_format_check_on_one_line": ["check", "format-check"],
    "comment_line_mentioning_ruff_check_is_ignored": ["check"],  # see note below
    "quoted_mention_inside_echo_is_not_a_real_invocation": [],
    "unrelated_recipe_line_is_ignored": [],
    "unparsable_line_is_ignored_not_raised": [],
    "ruff_global_flag_before_subcommand_is_not_recognized": [],
}


@pytest.mark.parametrize("case_id", sorted(_CLASSIFIER_CASES))
def test_ruff_invocation_classifier_classifies_synthetic_command_lines_correctly(
    case_id: str,
) -> None:
    """Given hand-authored command lines covering plain and `uv`-wrapped
    `ruff check`/`ruff format --check` invocations, extra flags, a
    mutating `ruff format` with no `--check` (must NOT count), an unrelated
    ruff subcommand, two invocations chained on one line, a quoted mention
    inside an `echo` (must NOT count -- it is not a real invocation), an
    unrelated recipe line, a line `shlex` cannot tokenize, and the
    documented "global flag before the subcommand" blind spot, when each is
    passed to `_ruff_invocations_in_line` directly, then it must return
    exactly the expected list of kinds.

    `comment_line_mentioning_ruff_check_is_ignored` is checked directly
    against `_ruff_invocations_in_line` here (which does NOT strip
    comments -- that is `_classify_lines`'s job, exercised by
    `test_comment_stripping_actually_removes_a_commented_out_ruff_invocation`
    below), so its expected result is `["check"]`: the raw line still
    tokenizes as a real invocation; comment-stripping is a separate,
    explicitly-tested responsibility layered on top.
    """
    line = _CLASSIFIER_CASES[case_id]
    expected = _CLASSIFIER_EXPECTED[case_id]
    kinds = [kind for kind, _ in _ruff_invocations_in_line(line)]
    assert kinds == expected, (
        f"case {case_id!r}: expected kinds {expected!r} for line {line!r}, got {kinds!r}"
    )


def test_comment_stripping_actually_removes_a_commented_out_ruff_invocation() -> None:
    """Given a commented-out `ruff check` recipe line (`_ruff_invocations_
    in_line` alone would still classify it -- see the note on
    `comment_line_mentioning_ruff_check_is_ignored` above), when it is
    passed through `_classify_lines` (what discovery actually uses), then
    it must be ignored -- proving comment-stripping is real, not merely
    assumed, and that a gate cannot be "discovered" purely because a
    disabled, commented-out recipe line mentions the right words."""
    line = _CLASSIFIER_CASES["comment_line_mentioning_ruff_check_is_ignored"]
    assert _classify_lines([line]) == []


# --- AC2, dynamic half: the gate's exit code reflects the real result -----


def _run_gate(gate: DiscoveredGate) -> subprocess.CompletedProcess[str]:
    """Run the discovered gate exactly as a contributor/CI would: `make
    <target>` for a Makefile gate, or the script directly for a script
    gate (`uv run python <script>` for a `.py` script, `bash <script>`
    otherwise). `stdin` is closed so a gate that unexpectedly waits for
    input is caught as a timeout rather than blocking this test forever."""
    if gate.kind == "makefile":
        argv = ["make", "--no-print-directory", gate.identifier]
    else:
        script_path = Path(gate.identifier)
        argv = (
            ["uv", "run", "python", str(script_path)]
            if script_path.suffix == ".py"
            else ["bash", str(script_path)]
        )
    return subprocess.run(
        argv,
        cwd=REPO_ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=GATE_SUBPROCESS_TIMEOUT_SECONDS,
        check=False,
    )


def _run_ruff_argv_independently(argv_from_ruff: list[str]) -> subprocess.CompletedProcess[str]:
    """`argv_from_ruff` starts with `"ruff"` (e.g. `["ruff", "check",
    "."]`). Run it through `uv run` so it resolves to this workspace's
    pinned `ruff` -- see the module docstring's "Why `ruff` invocations are
    extracted and re-run via `uv run ruff ...`" section for why this does
    not need to reproduce however the gate itself spells its wrapper."""
    return subprocess.run(
        ["uv", "run", *argv_from_ruff],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=GATE_SUBPROCESS_TIMEOUT_SECONDS,
        check=False,
    )


def test_gate_exit_code_reflects_the_combined_result_of_ruff_check_and_ruff_format_check() -> None:
    """Given the discovered Python lint gate, when it is run, then its exit
    code must be zero if and only if every `ruff` invocation extracted from
    it -- re-run directly and independently via `uv run ruff ...` -- also
    exits zero. Issue #28 (AC2's exit-code requirement: "exit-koden MÅSTE
    spegla resultatet").

    Deliberately does not assert the gate currently passes or currently
    fails: it computes, from the real repository state at the moment this
    test runs, what the correct combined result *is* right now (today,
    every real `ruff check .` and `ruff format --check .` invocation this
    module has measured fails, so the correct combined result is currently
    "fail" -- but this test does not hardcode that; it recomputes it from a
    live subprocess run every time), and checks the gate agrees with that.
    This is what catches a gate that always exits 0 regardless of `ruff`'s
    own result (e.g. `ruff check . || true`, or a Makefile recipe line
    prefixed with `-`), or a gate that silently only runs one of the two
    required commands while claiming, structurally, to cover both."""
    if _UV_BINARY is None:
        pytest.skip("uv is not on PATH; cannot re-run the extracted ruff invocations.")

    gate = _discover_python_lint_gate()
    if gate is None:
        pytest.skip(
            "no Python lint gate discovered yet -- see "
            "test_a_python_lint_gate_exists_as_a_discoverable_makefile_target_or_script, "
            "which is what carries the red signal for that. Nothing to run here yet."
        )
    if gate.kind == "makefile" and _MAKE_BINARY is None:
        pytest.skip("make is not on PATH; cannot run the discovered Makefile gate.")

    invocations = _invocations_in_lines(gate.lines)
    assert invocations, (
        f"internal inconsistency: {gate!r} was discovered as covering both a 'ruff check' and a "
        "'ruff format --check' invocation, but re-extracting invocations from its own lines "
        "found none. This should be impossible given how discovery itself works; if it happens, "
        "_ruff_invocations_in_line and _classify_lines/_invocations_in_lines have diverged."
    )

    independent_results = [
        (kind, argv, _run_ruff_argv_independently(argv)) for kind, argv in invocations
    ]
    expected_success = all(result.returncode == 0 for _, _, result in independent_results)

    gate_result = _run_gate(gate)
    gate_success = gate_result.returncode == 0

    independent_summary = "\n".join(
        f"  {kind}: {' '.join(argv)!r} -> returncode={result.returncode}"
        for kind, argv, result in independent_results
    )
    assert gate_success == expected_success, (
        f"gate {gate.identifier!r} ({gate.kind}) exited with returncode={gate_result.returncode!r} "
        f"(success={gate_success}), but independently re-running every 'ruff' invocation extracted "
        f"from its own command lines gives expected success={expected_success}:\n"
        f"{independent_summary}\n"
        f"--- gate stdout ---\n{gate_result.stdout}\n--- gate stderr ---\n{gate_result.stderr}\n"
        "The gate's exit code must reflect the real combined result of 'ruff check' and 'ruff "
        "format --check', not a hardcoded or swallowed one (issue #28, AC2)."
    )
