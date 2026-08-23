"""Tests for issue #23: `frontend/package.json`'s `lint` script (`next lint`)
cannot be used as a mechanical lint gate.

`frontend/package.json` declares `"lint": "next lint"`, but at authoring time
`eslint` is neither a `dependency` nor a `devDependency`, and no ESLint
configuration file (`eslint.config.*` flat config or legacy `.eslintrc*`)
exists anywhere under `frontend/`. Because of that, `next lint` (and
therefore `npm run lint`) does not run a check at all -- it starts Next's
interactive "How would you like to configure ESLint?" setup wizard instead.
Verified directly at authoring time, twice, with stdin closed (`< /dev/null`,
matching how a non-interactive CI runner or review step would invoke it):

    $ npm run lint < /dev/null
    > energy-frontend@0.1.0 lint
    > next lint

    ? How would you like to configure ESLint? https://nextjs.org/docs/app/api-reference/config/eslint
    [?25l>  Strict (recommended)
       Base
       Cancel
    (exit code 1)

Setting `CI=true` (the environment variable GitHub Actions itself sets on
every job, and the exact signal many CLI tools use to suppress interactive
prompts) does not change this: the identical prompt text and exit code 1 were
observed with `CI=true npm run lint < /dev/null` as well. So this is not a
"CI happens to look like a tty" false alarm -- `next lint` shows this same
wizard in a real GitHub Actions run, which is exactly the failure mode the
issue describes ("Kommandot kan alltsa inte anvandas i CI").

This module holds four tests, mapped to the issue's three acceptance
criteria:

1. `test_frontend_has_an_eslint_configuration_file` (AC1): a flat
   (`eslint.config.*`) or legacy (`.eslintrc*`) ESLint config file must exist
   under `frontend/`. Deliberately does not care which format, which parser,
   or which rules it configures -- picking the ruleset is Gate 4's decision,
   not this test's.
2. `test_frontend_package_json_declares_eslint_as_a_dev_dependency` (AC2):
   `eslint` must be a key in `frontend/package.json`'s `devDependencies`.
   Deliberately does not pin a version range.
3. `test_interactive_setup_prompt_detector_classifies_known_samples_correctly`
   (supporting AC3): a synthetic, dependency-free check that
   `_looks_like_aborted_interactive_setup_prompt` -- the function the next
   test uses to tell "a real lint result" apart from "an aborted setup
   wizard" -- classifies a real captured wizard transcript as True and a
   plausible real ESLint result transcript (both a clean pass and a
   problems-found run) as False. Exists so the detector's own correctness is
   demonstrated independently of whichever repository state
   `frontend/node_modules` happens to be in when the suite runs.
4. `test_lint_script_runs_noninteractively_without_hanging_or_starting_a_setup_prompt`
   (AC3, the core behavioral check): actually runs `npm run lint` -- the
   literal script `frontend/package.json` defines today, whatever it is
   rewritten to by Gate 4 -- with stdin closed and a bounded timeout, and
   asserts (a) it does not hang waiting for input, and (b) its combined
   output does not match the aborted-setup-wizard signature, so exit code 1
   can only mean "ESLint found problems", never "the wizard could not run
   interactively". This is deliberately a real-world subprocess run, not a
   mock: a test that only checked `frontend/package.json` for the string
   `"eslint"` would pass even though the command still hangs a reviewer's
   terminal or blocks CI, which is the actual defect issue #23 describes.

-- Why `npm run lint`, not `next lint` or `eslint .` directly --

`npm run lint` is the exact command a contributor, a review script, or a
future CI lint step would invoke (it is `frontend/package.json`'s own `lint`
script). Invoking `next lint` or `eslint .` directly would silently stop
testing whatever `package.json`'s `lint` script actually resolves to once
Gate 4 edits it (for example, `next lint` itself prints, at authoring time,
"`next lint` is deprecated and will be removed in Next.js 16" on stderr and
recommends migrating to a plain `eslint` CLI invocation -- Gate 4 may
reasonably rewrite the script to `"eslint ."` instead of keeping `next
lint`). Running the npm script keeps this test correct either way.

-- Why stdin is `subprocess.DEVNULL`, not a pty --

`subprocess.DEVNULL` gives an immediately-EOF, tty-less stdin, which is
exactly the environment a CI runner or a piped review-tool invocation
provides (verified as `< /dev/null` above, and cross-checked with `CI=true`
set). A pty would let a real interactive prompt block indefinitely rather
than resolve one way or the other, which the fixed command must never do
either way -- but importantly, this repository's own root-level
`conftest.py::block_outbound_http` fixture only blocks *outbound HTTP*, not
subprocesses, so no local pty/network setup is needed here.

-- Why the timeout is 120 seconds --

Matches the timeout `tests/test_frontend_vitest_globals_typecheck.py` uses
for `tsc --noEmit` against this same `frontend/` tree (also a whole-project
static-analysis pass, over a comparable file count) -- reusing an existing,
already-reasoned-about number in this test family instead of inventing a new
one. It is generous relative to what has actually been measured here: the
current, broken, aborted-wizard run completes in ~0.3 seconds (well under
even a tight timeout), so today's failure is driven entirely by the
prompt-content assertion below, not by hitting this timeout. The timeout
exists to bound a *future* regression (e.g. a fix that reintroduces some
other wait-for-input code path), not to make today's already-fast failure
pass.

-- Side effects --

`git status --porcelain` was empty both before and after every manual
`npm run lint`/`next lint` invocation performed while authoring this module
(including under `CI=true`), and `git clean -ndx frontend` lists only the
pre-existing, `.gitignore`d `frontend/node_modules/`, `frontend/.next/`, and
`frontend/tsconfig.tsbuildinfo` (see repository-root `.gitignore` lines 16,
17, and 22) -- none of them created by the lint invocation itself. So this
test needs no `tmp_path` redirection the way the `tsc` test does for
`tsconfig.tsbuildinfo`.

-- Why this module can only meaningfully run where `frontend/node_modules`
exists --

Same asymmetry documented in `tests/test_frontend_vitest_globals_typecheck.py`
and `tests/test_frontend_node_version_pinning.py`: `.github/workflows/
test.yml`'s `python` job (which is what runs this file in CI, per
`testpaths` in `pyproject.toml`) never runs `npm ci`; only the `frontend` job
does. `test_lint_script_runs_noninteractively_without_hanging_or_starting_a_setup_prompt`
skips, rather than fails, when `frontend/node_modules/.bin/next` or an `npm`
executable is absent, so it does not turn red in an environment it was never
able to check. `test_frontend_has_an_eslint_configuration_file` and
`test_frontend_package_json_declares_eslint_as_a_dev_dependency` need no
`node_modules` at all (they only read files) and always run.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / "frontend"
FRONTEND_PACKAGE_JSON = FRONTEND_DIR / "package.json"
NEXT_BINARY = FRONTEND_DIR / "node_modules" / ".bin" / "next"

# How long `npm run lint` is allowed to run before this test concludes it is
# hanging rather than merely slow. See the module docstring's "Why the
# timeout is 120 seconds" section for why this specific number was chosen.
LINT_SUBPROCESS_TIMEOUT_SECONDS = 120

# The exact, verbatim question Next's interactive ESLint setup wizard prints
# as the first line of its prompt (captured from real `npm run lint </dev/null`
# and `CI=true npm run lint </dev/null` output at authoring time -- see the
# module docstring). A real ESLint run -- whether clean or reporting
# problems -- never prints this literal question, so its presence in a lint
# invocation's combined output is a reliable signal that the wizard started
# instead of a real check running.
INTERACTIVE_SETUP_PROMPT_MARKER = "How would you like to configure ESLint?"

# Verbatim transcript captured from `npm run lint < /dev/null` at authoring
# time via `subprocess.run(..., capture_output=True, text=True)`, joined as
# `f"{stdout}\n{stderr}"` -- the exact same join
# `test_lint_script_runs_noninteractively_without_hanging_or_starting_a_setup_prompt`
# performs below, so this fixture matches what that test actually feeds the
# detector (ANSI "hide cursor" escape kept as `\x1b[?25l`). Used below only
# to prove the detector recognizes the real thing, not a paraphrase of it.
_CAPTURED_ABORTED_WIZARD_STDOUT = (
    "\n> energy-frontend@0.1.0 lint\n> next lint\n\n"
    "? How would you like to configure ESLint? "
    "https://nextjs.org/docs/app/api-reference/config/eslint\n"
    "\x1b[?25l❯  Strict (recommended)\n   Base\n   Cancel"
)
_CAPTURED_ABORTED_WIZARD_STDERR = (
    "`next lint` is deprecated and will be removed in Next.js 16.\n"
    "For new projects, use create-next-app to choose your preferred linter.\n"
    "For existing projects, migrate to the ESLint CLI:\n"
    "npx @next/codemod@canary next-lint-to-eslint-cli .\n\n"
    " ⚠ If you set up ESLint yourself, we recommend adding the Next.js ESLint plugin. "
    "See https://nextjs.org/docs/app/api-reference/config/eslint#migrating-existing-config\n"
)
_CAPTURED_ABORTED_WIZARD_TRANSCRIPT = (
    f"{_CAPTURED_ABORTED_WIZARD_STDOUT}\n{_CAPTURED_ABORTED_WIZARD_STDERR}"
)

# Plausible real ESLint CLI transcripts (clean pass and problems-found run),
# hand-authored from ESLint's own documented default output format
# (https://eslint.org/docs/latest/use/command-line-interface#--format), used
# to prove the detector does not also flag a genuine result as the aborted
# wizard.
_PLAUSIBLE_CLEAN_LINT_TRANSCRIPT = "\n> energy-frontend@0.1.0 lint\n> eslint .\n\n"
_PLAUSIBLE_PROBLEMS_FOUND_LINT_TRANSCRIPT = (
    "\n> energy-frontend@0.1.0 lint\n> eslint .\n\n"
    "/frontend/src/lib/brand.ts\n"
    "  12:5  error  'unused' is defined but never used  @typescript-eslint/no-unused-vars\n\n"
    "✖ 1 problem (1 error, 0 warnings)\n"
)


def _looks_like_aborted_interactive_setup_prompt(output: str) -> bool:
    """Return whether `output` (a lint invocation's combined stdout+stderr)
    contains Next's interactive ESLint setup wizard's opening question --
    i.e. whether the invocation started the wizard instead of running a real
    lint check. See `INTERACTIVE_SETUP_PROMPT_MARKER`'s docstring for why
    this exact substring is a reliable signal."""
    return INTERACTIVE_SETUP_PROMPT_MARKER in output


def _read_frontend_package_json() -> dict:
    return json.loads(FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8"))


# --- AC1: an ESLint configuration file exists under frontend/ ---------------


def _find_eslint_config_files() -> list[Path]:
    """Return every non-empty file directly under `frontend/` matching
    ESLint's flat-config (`eslint.config.*`) or legacy (`.eslintrc*`) naming
    convention (https://eslint.org/docs/latest/use/configure/configuration-files,
    https://eslint.org/docs/v8.x/use/configure/configuration-files-deprecated).
    Deliberately does not care which extension/format is used -- Gate 4
    picks the concrete config shape, not this test."""
    candidates = list(FRONTEND_DIR.glob("eslint.config.*")) + list(FRONTEND_DIR.glob(".eslintrc*"))
    return [path for path in candidates if path.is_file() and path.stat().st_size > 0]


def test_frontend_has_an_eslint_configuration_file() -> None:
    """Given `frontend/`, when it is searched for an ESLint configuration
    file, then at least one non-empty `eslint.config.*` (flat config, what
    Next 15 -- the version installed here, 15.5.23 at authoring time --
    supports) or `.eslintrc*` (legacy) file must exist. Issue #23 (AC1)."""
    config_files = _find_eslint_config_files()
    assert config_files, (
        f"expected at least one non-empty 'eslint.config.*' or '.eslintrc*' file directly "
        f"under {FRONTEND_DIR.relative_to(REPO_ROOT)}; found none. Without one, "
        "'next lint' has nothing to configure itself from and falls back to its "
        "interactive setup wizard (issue #23)."
    )


# --- AC2: eslint is declared as a devDependency -----------------------------


def test_frontend_package_json_declares_eslint_as_a_dev_dependency() -> None:
    """Given `frontend/package.json`, when its `devDependencies` are read,
    then `eslint` must be one of them. Issue #23 (AC2). Deliberately does not
    pin a version range -- only that the package is declared at all, which is
    what is missing today."""
    package_json = _read_frontend_package_json()
    dev_dependencies = package_json.get("devDependencies", {})
    assert "eslint" in dev_dependencies, (
        f"expected 'eslint' in {FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)}'s "
        f"'devDependencies'; found devDependencies={sorted(dev_dependencies)}. Without it, "
        "'next lint' (or a plain 'eslint' CLI) has no linter package to actually run "
        "(issue #23)."
    )


# --- AC3: the lint script is a real, non-interactive check ------------------


@pytest.mark.parametrize(
    ("transcript", "expected"),
    [
        pytest.param(_CAPTURED_ABORTED_WIZARD_TRANSCRIPT, True, id="real_captured_aborted_wizard"),
        pytest.param(_PLAUSIBLE_CLEAN_LINT_TRANSCRIPT, False, id="plausible_clean_lint_result"),
        pytest.param(
            _PLAUSIBLE_PROBLEMS_FOUND_LINT_TRANSCRIPT,
            False,
            id="plausible_problems_found_lint_result",
        ),
    ],
)
def test_interactive_setup_prompt_detector_classifies_known_samples_correctly(
    transcript: str, expected: bool
) -> None:
    """Given a real, verbatim-captured aborted-wizard transcript and two
    plausible real ESLint CLI transcripts (a clean pass and a run that found
    problems), when each is checked by
    `_looks_like_aborted_interactive_setup_prompt`, then only the real
    aborted-wizard transcript must be classified as such -- proving the
    detector `test_lint_script_runs_noninteractively_without_hanging_or_starting_a_setup_prompt`
    relies on neither false-negatives on the real bug nor false-positives on
    a genuine lint result, independent of whichever state
    `frontend/node_modules` happens to be in when this suite runs."""
    assert _looks_like_aborted_interactive_setup_prompt(transcript) is expected


@pytest.mark.skipif(
    not NEXT_BINARY.is_file() or shutil.which("npm") is None,
    reason=(
        f"{NEXT_BINARY} does not exist or no 'npm' executable is on PATH -- "
        "frontend/node_modules is not installed here. This repository's CI `python` job "
        "never runs `npm ci` (only the `frontend` job does), so this test cannot run there "
        "either; run `npm ci` inside frontend/ to exercise it locally."
    ),
)
def test_lint_script_runs_noninteractively_without_hanging_or_starting_a_setup_prompt() -> None:
    """Given `frontend/package.json`'s `lint` script, when it is run the way
    a non-interactive CI runner or review step would (`npm run lint` with
    stdin closed, no tty), then it must (a) finish within
    `LINT_SUBPROCESS_TIMEOUT_SECONDS` instead of hanging, and (b) its
    combined stdout+stderr must not contain Next's interactive ESLint setup
    wizard's opening question -- i.e. exit code 1 may only ever mean "ESLint
    found problems", never "the wizard could not run interactively because
    there is no tty". Issue #23 (AC3) -- this is deliberately a real
    subprocess run against the actual npm script, not a check of
    `package.json`'s text, per the module docstring's "Why `npm run lint`"
    section: a text-only check would pass even though the command still
    blocks a non-interactive caller exactly as described in the issue."""
    try:
        completed = subprocess.run(
            ["npm", "run", "lint"],
            cwd=FRONTEND_DIR,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=LINT_SUBPROCESS_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(
            f"'npm run lint' (stdin closed, cwd={FRONTEND_DIR.relative_to(REPO_ROOT)}) did not "
            f"finish within {LINT_SUBPROCESS_TIMEOUT_SECONDS}s -- it is hanging, most likely "
            "waiting for interactive input on a wizard that has no tty to read from "
            f"(issue #23). Partial output captured before the timeout: "
            f"stdout={exc.stdout!r} stderr={exc.stderr!r}"
        )

    combined_output = f"{completed.stdout}\n{completed.stderr}"
    assert not _looks_like_aborted_interactive_setup_prompt(combined_output), (
        "'npm run lint' (stdin closed) printed Next's interactive ESLint setup wizard's "
        f"opening question ({INTERACTIVE_SETUP_PROMPT_MARKER!r}) instead of running a real "
        "lint check -- this is issue #23: without an ESLint config and dependency, 'next "
        "lint' cannot run a check at all and falls back to a wizard that cannot be answered "
        f"non-interactively. returncode={completed.returncode!r}\n"
        f"stdout={completed.stdout!r}\nstderr={completed.stderr!r}"
    )

    assert completed.returncode in (0, 1), (
        "'npm run lint' (stdin closed) exited with returncode="
        f"{completed.returncode!r}, which is neither 0 (clean) nor 1 (ESLint's own "
        "'problems found' code) -- a code outside {0, 1} here (e.g. ESLint's own fatal "
        "'2', or any other non-lint exit path) means the invocation did not resolve to a "
        f"real lint result. stdout={completed.stdout!r}\nstderr={completed.stderr!r}"
    )
