"""Tests for issue #21: TypeScript does not know Vitest's injected globals
(`describe`, `it`, `expect`, `beforeEach`, ...).

`frontend/vitest.config.ts` sets `test.globals = true`, which makes Vitest
inject `describe`/`it`/`test`/`expect`/`beforeEach`/`afterEach`/`beforeAll`/
`afterAll`/`vi` into the global scope at *runtime* -- and that is exactly
why `npm test` (`vitest run`, esbuild-transpiled, no static type-checking)
has passed 253/253 tests the entire time this bug existed. Nothing about
`vitest run`'s transpile-only pipeline notices that `frontend/tsconfig.json`
declares no `compilerOptions.types` array at all, so TypeScript's own
ambient-global resolution -- which needs either an explicit
`types: ["vitest/globals"]` entry (matching `vitest/globals.d.ts`'s own
documented setup: https://vitest.dev/config/#globals) or an explicit
`import { describe, it, ... } from "vitest"` in every test file if
`globals` is instead left at `false` -- never picks up Vitest's global type
declarations. Running `npx tsc --noEmit` in `frontend/` is the only thing
in this repository that currently notices: it reports `TS2304 Cannot find
name 'X'` (for names with no better-known ambient home, e.g. `beforeEach`,
`expect`) and `TS2582 Cannot find name 'X'. Do you need to install type
definitions for a test runner?` (for names TypeScript happens to recognize
from some *other* ambient test-runner shim it ships with, e.g. `describe`,
`it`) -- 7 errors across `src/components/VirtualEvseDiagnosticsPanel.test.tsx`
and `src/lib/brand.test.ts`, measured at authoring time.

Two tests live here, one per acceptance criterion:

1. `test_tsconfig_types_and_vitest_config_globals_are_consistent` (AC1): a
   static, dependency-free consistency check between the two config files
   -- no `tsc` invocation needed, so it also runs somewhere
   `frontend/node_modules` was never installed. It accepts either
   self-consistent state (`globals: true` paired with `"vitest/globals"` in
   `compilerOptions.types`, or `globals: false` with no such entry needed)
   and fails only the current contradiction: `globals: true` with no
   `types` array at all, so nothing tells TypeScript where the injected
   globals' ambient declarations live.
2. `test_tsc_reports_no_vitest_global_name_errors` (AC2): the real-world
   check -- actually runs `frontend/node_modules/.bin/tsc --noEmit` (the
   exact command measured at authoring time to report 11 errors: 7 in the
   class this issue is about, TS2304/TS2582 for the missing Vitest
   globals, plus 4 unrelated TS2739/TS2741/TS2345 errors in test-fixture
   object literals that pre-date this issue and are tracked separately).
   This test asserts only that the TS2304/TS2582-for-a-known-Vitest-global
   class is empty. It deliberately does not assert zero `tsc` errors
   overall, so it neither blocks on, nor needs editing for, that separate
   pre-existing class -- see `_is_missing_vitest_global_diagnostic` and the
   docstring on the test itself.

-- Why this module can only meaningfully run where `frontend/node_modules`
exists, and why that will not be true in `.github/workflows/test.yml`'s
`python` job --

`tests/test_frontend_node_version_pinning.py` documents the same asymmetry
for a different reason (there: why `engines.node` is read from
`package-lock.json` instead of `node_modules`). Here: `.github/workflows/
test.yml`'s `python` job (which is what runs this `tests/` module in CI,
per `testpaths` in `pyproject.toml`) never runs `npm ci` -- only the
`frontend` job does, and that job's own `npm test` script is `vitest run`,
which never invokes `tsc` either (verified against `frontend/package.json`
at authoring time: there is no `typecheck` script). So today, *neither* CI
job runs a TypeScript type-check anywhere in this repository;
`test_tsc_reports_no_vitest_global_name_errors` below is the first thing
to do so, and it can only actually verify the real compiler's output where
`frontend/node_modules/.bin/tsc` exists (i.e. after a local `npm ci`, or a
future CI job that runs one before invoking pytest). It skips, rather than
fails, when that binary is absent -- consistent with the
`_MAKE_BINARY`/`_UV_BINARY` skip pattern in
`tests/test_collector_dev_finds_the_seeded_database.py` -- so this module
does not turn red in an environment it was never able to check. This CI
coverage gap (no job currently runs `tsc --noEmit` at all) is itself a
separate, pre-existing finding, out of issue #21's scope.

-- Why `tsc` is invoked as `frontend/node_modules/.bin/tsc` and not
`npx tsc` --

`npx` can fall back to a registry lookup if it does not find a local
binary; invoking the installed binary directly cannot, which keeps this
test consistent with the root `conftest.py::block_outbound_http` guard
against tests depending on real network access, and is also faster (no
`npx` resolution overhead).

-- Why `--tsBuildInfoFile` points at a `tmp_path` --

`frontend/tsconfig.json` sets `compilerOptions.incremental: true`, so a
plain `tsc --noEmit` run (confirmed at authoring time) writes
`frontend/tsconfig.tsbuildinfo` as a side effect even though nothing is
emitted otherwise. That file is `.gitignore`d (`frontend/.gitignore:22`,
`*.tsbuildinfo`), so it does not show up in `git status`, but leaving a
stray, repeatedly-overwritten file behind on every test run is still an
avoidable side effect of a test -- `--tsBuildInfoFile <tmp_path>/...`
redirects it into pytest's per-test temporary directory instead, which
pytest itself cleans up, so this test's `frontend/` working tree is
untouched (confirmed at authoring time: `git status --porcelain` inside
`frontend/` shows nothing new after running this test).
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / "frontend"
TSCONFIG_PATH = FRONTEND_DIR / "tsconfig.json"
VITEST_CONFIG_PATH = FRONTEND_DIR / "vitest.config.ts"
TSC_BINARY = FRONTEND_DIR / "node_modules" / ".bin" / "tsc"

VITEST_GLOBALS_TYPES_ENTRY = "vitest/globals"

# Every ambient global name Vitest injects when `test.globals` is `true`,
# per `frontend/node_modules/vitest/globals.d.ts` (verified at authoring
# time). TypeScript reports one of two different "unknown name" codes
# depending on whether it happens to already recognize the name from some
# *other* ambient test-runner shim it ships with (`describe`/`it` ->
# TS2582, "do you need @types/jest?") or not at all (`expect`/
# `beforeEach`/... -> TS2304).
VITEST_INJECTED_GLOBAL_NAMES = frozenset(
    {
        "describe",
        "it",
        "test",
        "expect",
        "beforeEach",
        "afterEach",
        "beforeAll",
        "afterAll",
        "vi",
    }
)

# TypeScript's two "unknown name" diagnostic codes that this issue can
# produce. TS2304 is a generic "Cannot find name" code with many unrelated
# causes (e.g. a genuine typo), so a diagnostic is only treated as "missing
# Vitest global" below when its code is one of these *and* the quoted name
# in its message is one of `VITEST_INJECTED_GLOBAL_NAMES` -- never by code
# alone.
_TS_UNKNOWN_NAME_CODES = frozenset({"TS2304", "TS2582"})

# Matches one `tsc --pretty false` diagnostic header line, e.g.:
#   src/lib/brand.test.ts(3,1): error TS2582: Cannot find name 'describe'.
# `tsc` may follow this with further, differently-indented continuation
# lines for multi-part messages (observed at authoring time for TS2345);
# those simply do not match this line-anchored pattern and are skipped,
# which is fine here since every TS2304/TS2582 message this test cares
# about is a single line.
_TSC_DIAGNOSTIC_RE = re.compile(
    r"^(?P<path>[^():]+)\((?P<line>\d+),(?P<column>\d+)\): error (?P<code>TS\d+): (?P<message>.*)$"
)

# TypeScript quotes the offending identifier in single quotes for both
# TS2304 ("Cannot find name 'X'.") and TS2582 ("Cannot find name 'X'. Do
# you need ..."); this pulls it back out.
_QUOTED_NAME_RE = re.compile(r"Cannot find name '([^']+)'")


def _load_tsconfig_types() -> list[str] | None:
    """Return `compilerOptions.types` from `frontend/tsconfig.json` as
    written (`None` if the key is absent entirely -- today's state,
    verified at authoring time)."""
    data = json.loads(TSCONFIG_PATH.read_text(encoding="utf-8"))
    return data["compilerOptions"].get("types")


# Anchored on the literal `globals:` key name, which is Vitest's own config
# key (https://vitest.dev/config/#globals). `vitest.config.ts` is
# TypeScript, not JSON/YAML, so this reads it as text rather than parsing
# it as a real config object (no Node.js dependency needed to evaluate a
# `defineConfig({...})` call from Python) -- `frontend/vitest.config.ts` is
# a small, hand-authored file, and `globals` appears exactly once in it
# (verified at authoring time), so this narrow regex is not reaching for
# more generality than the file actually has.
_VITEST_CONFIG_GLOBALS_RE = re.compile(r"\bglobals\s*:\s*(true|false)\b")


def _load_vitest_config_globals() -> bool:
    """Return `test.globals` from `frontend/vitest.config.ts` as a Python
    bool."""
    text = VITEST_CONFIG_PATH.read_text(encoding="utf-8")
    matches = _VITEST_CONFIG_GLOBALS_RE.findall(text)
    assert len(matches) == 1, (
        f"Expected exactly one `globals: true|false` key in {VITEST_CONFIG_PATH}; found "
        f"{len(matches)}. This test's regex assumption about the file's shape needs "
        "revisiting."
    )
    return matches[0] == "true"


def test_tsconfig_types_and_vitest_config_globals_are_consistent() -> None:
    """Given `frontend/vitest.config.ts` and `frontend/tsconfig.json`, when
    `test.globals` is `true` (Vitest injects `describe`/`it`/`expect`/
    `beforeEach`/... as ambient globals at runtime), then
    `compilerOptions.types` must include `"vitest/globals"` so TypeScript's
    ambient-global resolution picks up the matching type declarations
    (`vitest/globals.d.ts`) -- otherwise every test file that uses an
    injected global fails to type-check (TS2304/TS2582), exactly as
    measured for `src/components/VirtualEvseDiagnosticsPanel.test.tsx` and
    `src/lib/brand.test.ts` at authoring time (issue #21).

    Given `test.globals` is instead `false`, then no particular `types`
    entry is required: test files are expected to `import` the names they
    use directly from `"vitest"`, which needs no ambient type declaration
    at all. Both of these are accepted as consistent; only the
    contradiction between them (globals injected at runtime, but no type
    declaration told about it) is rejected.
    """
    globals_enabled = _load_vitest_config_globals()
    types = _load_tsconfig_types()

    if not globals_enabled:
        return

    assert types is not None and VITEST_GLOBALS_TYPES_ENTRY in types, (
        f"{VITEST_CONFIG_PATH} sets `test.globals: true`, so Vitest injects "
        "`describe`/`it`/`expect`/`beforeEach`/... as ambient globals at runtime; but "
        f"{TSCONFIG_PATH}'s `compilerOptions.types` is {types!r}, which does not include "
        f"{VITEST_GLOBALS_TYPES_ENTRY!r}. Add {VITEST_GLOBALS_TYPES_ENTRY!r} to "
        "`compilerOptions.types` (or set `test.globals: false` in vitest.config.ts and "
        "import the names explicitly in every test file) so TypeScript recognizes the "
        "names Vitest injects at runtime."
    )


def _tsc_diagnostics(output: str) -> list[dict[str, str]]:
    """Return every `tsc --pretty false` diagnostic header line in `output`
    that matches `_TSC_DIAGNOSTIC_RE`, each as a `{path, line, column,
    code, message}` dict."""
    diagnostics = []
    for line in output.splitlines():
        match = _TSC_DIAGNOSTIC_RE.match(line)
        if match:
            diagnostics.append(match.groupdict())
    return diagnostics


def _is_missing_vitest_global_diagnostic(diagnostic: dict[str, str]) -> bool:
    """A diagnostic is "the class issue #21 is about" only if it is
    TS2304/TS2582 *and* the quoted name in its message is one of Vitest's
    injected globals -- never by diagnostic code alone, since TS2304 in
    particular is a generic "unknown identifier" code (e.g. a genuine typo
    would also be TS2304, and must not be silently treated as this issue)."""
    if diagnostic["code"] not in _TS_UNKNOWN_NAME_CODES:
        return False
    name_match = _QUOTED_NAME_RE.search(diagnostic["message"])
    return bool(name_match) and name_match.group(1) in VITEST_INJECTED_GLOBAL_NAMES


@pytest.mark.skipif(
    not TSC_BINARY.is_file(),
    reason=(
        f"{TSC_BINARY} does not exist -- frontend/node_modules is not installed here. This "
        "repository's CI `python` job never runs `npm ci` (only the `frontend` job does), "
        "so this test cannot run there either; run `npm ci` inside frontend/ to exercise it "
        "locally."
    ),
)
def test_tsc_reports_no_vitest_global_name_errors(tmp_path: Path) -> None:
    """Given `frontend/`'s real TypeScript configuration, when
    `tsc --noEmit` type-checks the project, then it must report zero
    TS2304/TS2582 "Cannot find name" errors for any of Vitest's injected
    globals (`describe`, `it`, `test`, `expect`, `beforeEach`, `afterEach`,
    `beforeAll`, `afterAll`, `vi`) -- issue #21.

    This intentionally does NOT assert zero `tsc` errors overall: 4
    unrelated errors exist at authoring time (TS2739/TS2741/TS2345 --
    missing fields in test-fixture object literals typed as
    `SolarForecastPoint`/`Site`/`HeartbeatConfigUpdate`, in
    `EnergyChart.test.tsx`, `SiteCard.test.tsx` and
    `api.extended.test.ts`) and are out of this issue's scope, tracked
    separately. Asserting zero errors overall would make this test fail
    for a reason issue #21's fix cannot address, and would need editing
    the moment that unrelated class is fixed independently -- with the
    narrower assertion below, this test does not need to change either
    way.
    """
    build_info_path = tmp_path / "vitest-globals-typecheck.tsbuildinfo"
    completed = subprocess.run(
        [
            str(TSC_BINARY),
            "--noEmit",
            "--pretty",
            "false",
            "--tsBuildInfoFile",
            str(build_info_path),
        ],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    diagnostics = _tsc_diagnostics(completed.stdout)
    if completed.returncode != 0:
        # `tsc` reported *something*; make sure this test's regex actually
        # parsed it, rather than passing vacuously because the output
        # format changed underneath it (e.g. moved to stderr, or restyled
        # its header line).
        assert diagnostics, (
            f"tsc exited non-zero ({completed.returncode}) but this test's regex found no "
            "parseable diagnostic lines in stdout; either tsc's output format changed and "
            f"`_TSC_DIAGNOSTIC_RE` needs updating, or output landed on stderr instead. "
            f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
        )

    missing_global_diagnostics = [d for d in diagnostics if _is_missing_vitest_global_diagnostic(d)]
    assert not missing_global_diagnostics, (
        "tsc --noEmit reported {} error(s) for one of Vitest's injected globals "
        "({}) not being recognized (TS2304/TS2582):\n{}\n\nThis means "
        "frontend/tsconfig.json's compilerOptions.types does not include "
        "'vitest/globals' while frontend/vitest.config.ts sets test.globals: true "
        "(issue #21).".format(
            len(missing_global_diagnostics),
            sorted(VITEST_INJECTED_GLOBAL_NAMES),
            "\n".join(
                f"{d['path']}({d['line']},{d['column']}): {d['code']}: {d['message']}"
                for d in missing_global_diagnostics
            ),
        )
    )
