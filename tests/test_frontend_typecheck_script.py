"""Tests for issue #17's `frontend/package.json` `typecheck` script.

`tests/test_frontend_vitest_globals_typecheck.py` (issue #21) established
that `npx tsc --noEmit` reports real errors this repository's `vitest run`
pipeline never notices, and that at authoring time 4 of those errors
(TS2739/TS2741/TS2345 in test-fixture object literals) pre-date issue #21
and are tracked separately as issue #55. That same module's docstring notes
`frontend/package.json` has no `typecheck` script at all -- so today there
is no single, discoverable command a contributor or a future CI step can
run to type-check the frontend.

Issue #17 (AC13) adds a `"typecheck": "tsc --noEmit"`-shaped script.
Deliberately, per the issue's own scope, this does **not** add a CI step
that runs it (AC15): with issue #55's 4 pre-existing errors still present,
wiring `npm run typecheck` into CI today would turn every otherwise-green
frontend PR red for a reason outside its author's control. This module
holds three tests, one per acceptance criterion:

1. `test_frontend_package_json_declares_a_typecheck_script_invoking_tsc_noemit`
   (AC13): a static check that `scripts.typecheck` exists and tokenizes to
   a `tsc` invocation carrying `--noEmit`.
2. `test_npm_run_typecheck_matches_direct_tsc_invocation` (AC14): the
   real-world check -- runs both `npm run typecheck` and a direct
   `frontend/node_modules/.bin/tsc --noEmit` invocation and asserts they
   report the same exit code and the same diagnostic set (by `(path,
   code)`), proving the script is a faithful wrapper around the real
   compiler rather than, say, pointing at a different `tsconfig.json` or
   swallowing errors. This deliberately never asserts either invocation
   exits 0 -- see the test's own docstring for why, and for why this is the
   one test in this module that cannot run in CI's `python` job.
3. `test_ci_workflow_never_runs_npm_run_typecheck` (AC15): a negative
   check that no CI job invokes `npm run typecheck` -- see that test's
   docstring for the issue #55 condition under which it should be removed.

-- Why AC13's test does not run `tsc` itself --

`scripts.typecheck` existing and being *shaped like* a `tsc --noEmit`
invocation is a property of `frontend/package.json`'s text alone -- it
needs no `frontend/node_modules` and so always runs, including in CI's
`python` job (which never runs `npm ci`, per the asymmetry
`tests/test_frontend_node_version_pinning.py` and
`tests/test_frontend_vitest_globals_typecheck.py` both document). Whether
the script actually *behaves* like `tsc --noEmit` when run for real is
`test_npm_run_typecheck_matches_direct_tsc_invocation`'s job, and that one
does need `node_modules` and skips without it.

-- Why `--tsBuildInfoFile` is redirected for both invocations --

`frontend/tsconfig.json` sets `compilerOptions.incremental: true`, so a
plain `tsc --noEmit` run writes `frontend/tsconfig.tsbuildinfo` as a side
effect (confirmed by `tests/test_frontend_vitest_globals_typecheck.py`'s own
"Why `--tsBuildInfoFile` points at a `tmp_path`" section, issue #59's
concern). The direct invocation here passes `--tsBuildInfoFile` on its own
command line the same way that module does. `npm run typecheck` cannot take
that flag as its own argument (`scripts.typecheck` is just `"tsc
--noEmit"`), but `npm run <script> -- <extra args>` forwards anything after
`--` to the underlying script, and `tsc` takes the last occurrence of a
repeated flag, so `npm run typecheck -- --tsBuildInfoFile <path>` redirects
the npm-wrapped invocation's build-info file into `tmp_path` exactly like
the direct one, without needing to know or assume anything else about how
`scripts.typecheck` is spelled.
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from _tsc_diagnostics import tsc_diagnostics

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / "frontend"
FRONTEND_PACKAGE_JSON = FRONTEND_DIR / "package.json"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "test.yml"
TSC_BINARY = FRONTEND_DIR / "node_modules" / ".bin" / "tsc"

TYPECHECK_SUBPROCESS_TIMEOUT_SECONDS = 120

NPM_RUN_TYPECHECK_TOKENS = ["npm", "run", "typecheck"]


def _read_frontend_package_json() -> dict:
    return json.loads(FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8"))


# --- AC13: frontend/package.json declares scripts.typecheck ----------------


def _typecheck_script_tokens() -> list[str] | None:
    """Return `frontend/package.json`'s `scripts.typecheck` entry, shell
    -tokenized, or `None` if no such script is declared."""
    package_json = _read_frontend_package_json()
    typecheck_script = package_json.get("scripts", {}).get("typecheck")
    if not typecheck_script:
        return None
    return shlex.split(typecheck_script)


def _is_tsc_invocation_with_no_emit(tokens: list[str]) -> bool:
    """Return whether `tokens` (a tokenized shell command) invokes `tsc`
    (either the bare command name or a path ending in `/tsc`, so both `"tsc
    --noEmit"` and `"./node_modules/.bin/tsc --noEmit"` are recognized) and
    includes the `--noEmit` flag somewhere in its arguments."""
    invokes_tsc = any(token == "tsc" or token.endswith("/tsc") for token in tokens)
    return invokes_tsc and "--noEmit" in tokens


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [
        pytest.param(["tsc", "--noEmit"], True, id="bare_tsc_with_noemit"),
        pytest.param(
            ["./node_modules/.bin/tsc", "--noEmit"], True, id="path_qualified_tsc_with_noemit"
        ),
        pytest.param(["tsc", "--noEmit", "--pretty", "false"], True, id="noemit_with_extra_flags"),
        pytest.param(["tsc"], False, id="tsc_without_noemit"),
        pytest.param(["eslint", "--noEmit"], False, id="noemit_without_tsc"),
        pytest.param(["next", "build"], False, id="unrelated_command"),
        pytest.param([], False, id="empty_tokens"),
    ],
)
def test_is_tsc_invocation_with_no_emit_classifies_synthetic_token_lists(
    tokens: list[str], expected: bool
) -> None:
    """Given synthetic tokenized commands covering a bare `tsc --noEmit`, a
    path-qualified `tsc --noEmit`, `--noEmit` alongside other flags, `tsc`
    without `--noEmit`, `--noEmit` on an unrelated command, and an unrelated
    command entirely, when each is classified, then only the ones that
    genuinely invoke `tsc` with `--noEmit` present must be recognized."""
    assert _is_tsc_invocation_with_no_emit(tokens) is expected


def test_frontend_package_json_declares_a_typecheck_script_invoking_tsc_noemit() -> None:
    """Given `frontend/package.json`, when its `scripts.typecheck` entry is
    read, then it must exist and its shell tokens must invoke `tsc` with
    `--noEmit` -- issue #17, AC13.

    Does not cover: whether running the script actually produces the same
    diagnostics as a direct `tsc --noEmit` invocation (that is
    `test_npm_run_typecheck_matches_direct_tsc_invocation`'s job), and does
    not require the script to exit 0 (issue #55's pre-existing errors mean
    it should not, today)."""
    tokens = _typecheck_script_tokens()
    assert tokens is not None, (
        f"expected a 'scripts.typecheck' entry in "
        f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)}; found scripts="
        f"{sorted(_read_frontend_package_json().get('scripts', {}))}"
    )
    assert _is_tsc_invocation_with_no_emit(tokens), (
        f"expected {FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)}'s 'scripts.typecheck' "
        f"({' '.join(tokens)!r}) to invoke 'tsc' with '--noEmit'."
    )


# --- AC14: npm run typecheck matches a direct tsc --noEmit invocation ------


def _diagnostic_identity_set(output: str) -> set[tuple[str, str]]:
    """Return the `(path, code)` pairs of every diagnostic `tsc_diagnostics`
    finds in `output`, as a set -- the identity this test compares between
    the two invocations. Line/column are deliberately excluded: both
    invocations type-check the exact same source files, so if the
    `--tsBuildInfoFile` redirection (this module's docstring, "Why
    `--tsBuildInfoFile` is redirected for both invocations") ever behaved
    differently between them and shifted incremental-build bookkeeping, a
    `(path, code)`-only comparison still correctly reports "same
    diagnostics" as long as the same errors were found in the same files,
    which is the property AC14 actually cares about."""
    return {(d["path"], d["code"]) for d in tsc_diagnostics(output)}


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        pytest.param("", set(), id="empty_output"),
        pytest.param(
            "a.ts(1,1): error TS2304: Cannot find name 'x'.\n",
            {("a.ts", "TS2304")},
            id="single_diagnostic",
        ),
        pytest.param(
            (
                "a.ts(1,1): error TS2304: Cannot find name 'x'.\n"
                "a.ts(2,1): error TS2304: Cannot find name 'x'.\n"
            ),
            {("a.ts", "TS2304")},
            id="duplicate_path_and_code_collapses_to_one_identity",
        ),
        pytest.param(
            (
                "a.ts(1,1): error TS2304: Cannot find name 'x'.\n"
                "b.ts(1,1): error TS2345: Argument of type 'x' is not assignable.\n"
            ),
            {("a.ts", "TS2304"), ("b.ts", "TS2345")},
            id="two_distinct_diagnostics",
        ),
    ],
)
def test_diagnostic_identity_set_classifies_synthetic_tsc_output(
    output: str, expected: set[tuple[str, str]]
) -> None:
    """Given synthetic `tsc --pretty false` output covering no diagnostics,
    one diagnostic, two diagnostics that share the same (path, code) at
    different line/columns, and two genuinely distinct diagnostics, when
    `_diagnostic_identity_set` reads it, then it must return exactly the
    expected set of `(path, code)` pairs, including collapsing same-identity
    duplicates."""
    assert _diagnostic_identity_set(output) == expected


@pytest.mark.skipif(
    not TSC_BINARY.is_file() or shutil.which("npm") is None,
    reason=(
        f"{TSC_BINARY} does not exist or no 'npm' executable is on PATH -- "
        "frontend/node_modules is not installed here. This repository's CI 'python' job "
        "never runs 'npm ci' (only the 'frontend' job does), so this test cannot run there "
        "either, and 'frontend'/'frontend-lint' jobs never run pytest at all -- meaning this "
        "test never runs inside this repository's own CI. Run 'npm ci' inside frontend/ to "
        "exercise it locally."
    ),
)
def test_npm_run_typecheck_matches_direct_tsc_invocation(tmp_path: Path) -> None:
    """Given `frontend/package.json`'s `typecheck` script and a direct
    `frontend/node_modules/.bin/tsc --noEmit` invocation, when both are run,
    then they must report the same exit code and the same `(path, code)`
    diagnostic set -- proving `npm run typecheck` is a faithful wrapper
    around the real compiler check rather than, e.g., pointing at a
    different `tsconfig.json`, swallowing errors, or silently no-op'ing
    because the script name does not exist yet.

    This deliberately never asserts either invocation exits 0: issue #55
    documents 4 pre-existing `tsc` errors in test-fixture object literals
    (`EnergyChart.test.tsx`, `SiteCard.test.tsx`, `api.extended.test.ts`),
    unrelated to issue #17, and not yet fixed -- measured directly at
    authoring time via `frontend/node_modules/.bin/tsc --noEmit --pretty
    false`: exit code 2, exactly those 4 diagnostics. So this suite is red
    by design (both invocations should fail, identically) until issue #55 is
    separately resolved; asserting exit 0 here would make this test
    reflect issue #55's status rather than AC14's.

    Today, before issue #17's `scripts.typecheck` is added, this test fails
    for the expected reason: `npm run typecheck` exits with npm's "Missing
    script" error (measured at authoring time: exit code 1, no parseable
    `tsc`-shaped diagnostics), which differs from the direct invocation's
    exit code 2 and 4 diagnostics on both axes this test checks.

    This is also the one test in this module that can never run inside this
    repository's own CI (see the `skipif` reason above), which is why the
    module docstring calls that out explicitly rather than leaving it to be
    discovered later."""
    direct_build_info = tmp_path / "direct-tsc.tsbuildinfo"
    direct = subprocess.run(
        [
            str(TSC_BINARY),
            "--noEmit",
            "--pretty",
            "false",
            "--tsBuildInfoFile",
            str(direct_build_info),
        ],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
        timeout=TYPECHECK_SUBPROCESS_TIMEOUT_SECONDS,
        check=False,
    )

    npm_executable = shutil.which("npm")
    assert npm_executable is not None  # narrows the type for mypy/pyright; guarded by skipif above
    npm_build_info = tmp_path / "npm-typecheck.tsbuildinfo"
    npm_run = subprocess.run(
        [
            npm_executable,
            "run",
            "typecheck",
            "--",
            "--pretty",
            "false",
            "--tsBuildInfoFile",
            str(npm_build_info),
        ],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
        timeout=TYPECHECK_SUBPROCESS_TIMEOUT_SECONDS,
        check=False,
    )

    direct_diagnostics = _diagnostic_identity_set(direct.stdout)
    npm_diagnostics = _diagnostic_identity_set(npm_run.stdout)

    assert npm_run.returncode == direct.returncode, (
        f"'npm run typecheck -- ...' exited {npm_run.returncode!r}, but a direct "
        f"'{TSC_BINARY.relative_to(REPO_ROOT)} --noEmit' exited {direct.returncode!r}. "
        f"npm stdout={npm_run.stdout!r} npm stderr={npm_run.stderr!r} "
        f"direct stdout={direct.stdout!r} direct stderr={direct.stderr!r}"
    )
    assert npm_diagnostics == direct_diagnostics, (
        "'npm run typecheck -- ...' and a direct "
        f"'{TSC_BINARY.relative_to(REPO_ROOT)} --noEmit' reported different (path, code) "
        f"diagnostic sets. npm-wrapped: {sorted(npm_diagnostics)}; direct: "
        f"{sorted(direct_diagnostics)}. npm stdout={npm_run.stdout!r} direct stdout="
        f"{direct.stdout!r}"
    )


# --- AC15: no CI job runs npm run typecheck ---------------------------------


def test_ci_workflow_never_runs_npm_run_typecheck() -> None:
    """Given `.github/workflows/test.yml`, when every job's steps are read,
    then none of them may run `npm run typecheck` -- issue #17 deliberately
    does not wire a CI typecheck step, because issue #55's 4 pre-existing
    `tsc` errors in test-fixture object literals (unrelated to issue #17)
    would turn every otherwise-green frontend PR red for a reason outside
    its author's control. **Remove this test once issue #55 is resolved**
    and a real CI typecheck step is deliberately added -- at that point this
    test's assertion becomes the wrong contract to hold.

    This assertion already holds today (no job runs `npm run typecheck`
    because the script itself does not exist yet), so it is a
    forward-looking regression guard rather than a red-to-green check: it
    exists to catch a future change that wires the script into CI before
    issue #55 is fixed, not to prove anything about today's workflow that
    isn't also true of an empty workflow."""
    workflow_data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))

    violations = []
    for job_name, job in workflow_data.get("jobs", {}).items():
        for step in job.get("steps", []):
            run_value = step.get("run")
            if not run_value:
                continue
            for line in str(run_value).splitlines():
                tokens = shlex.split(line) if line.strip() else []
                window = len(NPM_RUN_TYPECHECK_TOKENS)
                if any(
                    tokens[i : i + window] == NPM_RUN_TYPECHECK_TOKENS
                    for i in range(len(tokens) - window + 1)
                ):
                    violations.append((job_name, line.strip()))

    assert not violations, (
        "expected no CI job to run 'npm run typecheck' (issue #55 tracks the pre-existing "
        f"tsc errors that block wiring this into CI); found it in: {violations}"
    )
