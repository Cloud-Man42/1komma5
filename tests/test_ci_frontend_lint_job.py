"""Tests for issue #17 (GH-17)'s dedicated `frontend-lint` CI job.

`tests/test_frontend_eslint_lint_gate.py` (issue #23) established that
`npm run lint` is a real, non-interactive ESLint check once an ESLint config
and dependency exist. But `.github/workflows/test.yml` never runs it: the
`frontend` job only runs `npm test` (Vitest). Issue #70 separately documents
that this repository's Vitest suite is measurably flaky under CPU
contention (11/12 green at 2 cores, matching a GitHub-hosted runner). Wiring
lint into the *same* job as that flaky suite would mean a spurious Vitest
retry-worthy failure and a genuine lint regression report through the same
CI signal, indistinguishable to a reviewer without reading the log. This
module holds two tests, one per acceptance criterion:

1. `test_ci_workflow_has_a_frontend_lint_job_running_npm_ci_then_lint`
   (AC4): a job named `frontend-lint` must exist, and its step chain must
   run `npm ci` before running the lint check (either the literal `npm run
   lint` invocation, or the exact command `frontend/package.json`'s own
   `lint` script currently resolves to -- this test does not care which
   spelling is used, only that *some* step actually runs the lint check
   after dependencies are installed).
2. `test_frontend_job_step_chain_has_no_lint_invocation` (AC6): the
   `frontend` job's own step chain must contain no lint invocation at all --
   lint lives only in `frontend-lint`, so a flaky Vitest run's CI status can
   never be conflated with a lint failure's.

-- Why `_is_lint_invocation` accepts two spellings --

AC4 explicitly allows either `npm run lint` (the npm-script wrapper) or
whatever command `frontend/package.json`'s `lint` script itself resolves to
(at authoring time, `"eslint ."`), because Gate 4 -- which writes the actual
CI job -- may reasonably invoke either the wrapper or the underlying tool
directly. Reading the expected "underlying tool" form from
`frontend/package.json` at test time (rather than hard-coding `"eslint
."`) keeps this test correct even if that script's own definition changes,
as long as whatever CI runs still matches it.

-- Why this module never runs `npm ci` or `npm run lint` itself --

Unlike `tests/test_frontend_eslint_lint_gate.py`, this module only reads
`.github/workflows/test.yml` (via PyYAML, following the precedent
`tests/test_frontend_node_version_pinning.py` documents for GH-32's sake) --
it never shells out to `npm`. What matters here is which commands CI is
*configured* to run and in what order, not whether those commands currently
succeed on this machine; the latter is already covered by
`tests/test_frontend_eslint_lint_gate.py`'s own real-subprocess test. That
also means this module needs no `frontend/node_modules` skip guard: it
always runs, everywhere `.github/workflows/test.yml` and
`frontend/package.json` exist -- which is everywhere in this repository.
"""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "test.yml"
FRONTEND_PACKAGE_JSON = REPO_ROOT / "frontend" / "package.json"

FRONTEND_LINT_JOB_NAME = "frontend-lint"
FRONTEND_JOB_NAME = "frontend"

NPM_CI_TOKENS = ["npm", "ci"]
NPM_RUN_LINT_TOKENS = ["npm", "run", "lint"]


def _read_frontend_package_json() -> dict:
    return json.loads(FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8"))


def _frontend_lint_script_tokens() -> list[str]:
    """Return the shell tokens of `frontend/package.json`'s `scripts.lint`
    entry -- the command `npm run lint` resolves to at runtime (e.g.
    `["eslint", "."]`)."""
    package_json = _read_frontend_package_json()
    lint_script = package_json.get("scripts", {}).get("lint")
    assert lint_script, (
        f"expected a 'scripts.lint' entry in {FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)}; "
        f"found scripts={sorted(package_json.get('scripts', {}))}"
    )
    return shlex.split(lint_script)


def _job_steps(workflow_data: dict, job_name: str) -> list[dict]:
    """Return `job_name`'s `steps` list from a parsed workflow document.
    Raises `AssertionError` naming the missing job if it does not exist."""
    job = workflow_data.get("jobs", {}).get(job_name)
    assert job is not None, (
        f"expected a {job_name!r} job in {WORKFLOW_PATH.relative_to(REPO_ROOT)}; found jobs="
        f"{sorted(workflow_data.get('jobs', {}))}"
    )
    return job.get("steps", [])


def _contains_command(tokens: list[str], command_tokens: list[str]) -> bool:
    """Return whether `command_tokens` appears as a contiguous run inside
    `tokens` -- so a chained shell command (e.g. `npm ci && npm run lint`,
    tokenized by `shlex.split` into `["npm", "ci", "&&", "npm", "run",
    "lint"]`) is still recognized as containing both `npm ci` and `npm run
    lint`, not just a single-command step."""
    window = len(command_tokens)
    if window == 0 or window > len(tokens):
        return False
    return any(tokens[i : i + window] == command_tokens for i in range(len(tokens) - window + 1))


def _step_run_lines(step: dict) -> list[str]:
    """Return every non-blank line of a step's `run:` command (a step with
    no `run:` key, e.g. a `uses:` step, yields an empty list). GitHub
    Actions' YAML block-scalar `run:` values can hold multiple shell lines;
    splitting on lines (rather than tokenizing the whole block at once)
    keeps `shlex.split` from tripping over line-spanning shell syntax it
    does not need to understand here."""
    run_value = step.get("run")
    if not run_value:
        return []
    return [line.strip() for line in str(run_value).splitlines() if line.strip()]


def _step_runs_command(step: dict, command_tokens: list[str]) -> bool:
    """Return whether any line of `step`'s `run:` command contains
    `command_tokens` as a contiguous token run."""
    return any(
        _contains_command(shlex.split(line), command_tokens) for line in _step_run_lines(step)
    )


def _is_lint_invocation(step: dict) -> bool:
    """Return whether `step` runs the frontend lint check -- either the
    literal `npm run lint` wrapper, or the exact command
    `frontend/package.json`'s own `lint` script resolves to. See this
    module's docstring ("Why `_is_lint_invocation` accepts two spellings")
    for why both are accepted."""
    return _step_runs_command(step, NPM_RUN_LINT_TOKENS) or _step_runs_command(
        step, _frontend_lint_script_tokens()
    )


# --- Synthetic self-tests for the parsing helpers ---------------------------


@pytest.mark.parametrize(
    ("tokens", "command_tokens", "expected"),
    [
        pytest.param(["npm", "ci"], ["npm", "ci"], True, id="exact_match"),
        pytest.param(
            ["npm", "ci", "&&", "npm", "run", "lint"],
            ["npm", "run", "lint"],
            True,
            id="command_after_a_chain_separator",
        ),
        pytest.param(
            ["npm", "run", "lint", "&&", "npm", "ci"],
            ["npm", "ci"],
            True,
            id="command_before_a_chain_separator",
        ),
        pytest.param(["npm", "test"], ["npm", "run", "lint"], False, id="unrelated_command"),
        pytest.param(
            ["npm", "run", "lintfoo"], ["npm", "run", "lint"], False, id="near_miss_token"
        ),
        pytest.param([], ["npm", "ci"], False, id="empty_tokens"),
    ],
)
def test_contains_command_finds_a_contiguous_subsequence(
    tokens: list[str], command_tokens: list[str], expected: bool
) -> None:
    """Given synthetic token lists covering an exact match, a match either
    side of a shell chain separator, an unrelated command, a token that is
    merely a near-miss substring, and an empty token list, when
    `_contains_command` checks for a contiguous match, then it must
    classify each case exactly as expected."""
    assert _contains_command(tokens, command_tokens) is expected


def test_is_lint_invocation_recognizes_the_npm_wrapper_and_the_resolved_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Given a synthetic `scripts.lint` resolving to `"eslint ."`, when a
    step running `npm run lint` and a step running `eslint .` directly are
    each checked, then both must be recognized as a lint invocation, and a
    step running an unrelated command must not."""
    monkeypatch.setattr(
        sys.modules[__name__], "_frontend_lint_script_tokens", lambda: ["eslint", "."]
    )
    assert _is_lint_invocation({"run": "npm run lint"}) is True
    assert _is_lint_invocation({"run": "eslint ."}) is True
    assert _is_lint_invocation({"run": "npm test"}) is False
    assert _is_lint_invocation({"uses": "actions/checkout@v5"}) is False


# --- AC4: a frontend-lint job runs npm ci before the lint check -------------


def test_ci_workflow_has_a_frontend_lint_job_running_npm_ci_then_lint() -> None:
    """Given .github/workflows/test.yml, when a `frontend-lint` job is
    looked up, then it must exist, at least one of its steps must run `npm
    ci`, at least one step must run the lint check (`npm run lint` or the
    resolved `scripts.lint` command), and the first such `npm ci` step must
    come before the first such lint step -- issue #17, AC4.

    Does not cover: whether `npm run lint` (or the resolved command) itself
    currently exits 0 or reports problems on this machine -- that is
    `tests/test_frontend_eslint_lint_gate.py`'s concern. This test only
    checks what CI is configured to run and in what order."""
    workflow_data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    steps = _job_steps(workflow_data, FRONTEND_LINT_JOB_NAME)

    npm_ci_indices = [i for i, step in enumerate(steps) if _step_runs_command(step, NPM_CI_TOKENS)]
    lint_indices = [i for i, step in enumerate(steps) if _is_lint_invocation(step)]

    assert npm_ci_indices, (
        f"expected the {FRONTEND_LINT_JOB_NAME!r} job to contain a step running 'npm ci'; "
        f"steps={steps}"
    )
    assert lint_indices, (
        f"expected the {FRONTEND_LINT_JOB_NAME!r} job to contain a step running the lint "
        f"check ('npm run lint' or the resolved 'scripts.lint' command); steps={steps}"
    )
    assert min(npm_ci_indices) < min(lint_indices), (
        f"expected the {FRONTEND_LINT_JOB_NAME!r} job's 'npm ci' step to come before its "
        f"lint step; npm_ci step index={min(npm_ci_indices)}, lint step index="
        f"{min(lint_indices)}, steps={steps}"
    )


# --- AC6: the frontend job's own step chain runs no lint invocation --------


def test_frontend_job_step_chain_has_no_lint_invocation() -> None:
    """Given .github/workflows/test.yml, when the `frontend` job's steps are
    read, then none of them may run the lint check -- lint must live only in
    the `frontend-lint` job, so a flaky Vitest run (issue #70) and a genuine
    lint regression stay two distinguishable CI signals instead of one
    conflated job status -- issue #17, AC6.

    This assertion already holds today (the `frontend` job currently only
    runs `npm test`, no lint step exists anywhere yet), so it is a
    regression guard rather than a red-to-green check by itself: it exists
    to catch Gate 4 adding a lint step to the wrong job, not to prove a lint
    step was added at all -- that is
    `test_ci_workflow_has_a_frontend_lint_job_running_npm_ci_then_lint`'s
    job."""
    workflow_data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    steps = _job_steps(workflow_data, FRONTEND_JOB_NAME)

    lint_steps = [step for step in steps if _is_lint_invocation(step)]
    assert not lint_steps, (
        f"expected the {FRONTEND_JOB_NAME!r} job to run no lint invocation; found: {lint_steps}"
    )
