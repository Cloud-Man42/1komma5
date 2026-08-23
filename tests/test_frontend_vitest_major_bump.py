"""Tests for issue #49: bump `vitest` and `@vitest/coverage-v8` from `^2.1.8`
to `^4.1.11`.

This module covers AC1, AC2, AC3, and AC9 of issue #49 -- every acceptance
criterion provable from files this repository already commits, without
running `npm ci` (see "-- Why this module never runs `npm ci` or a live
`npm view` --" below). AC6 lives in `tests/test_frontend_node_version_pinning.py`
instead (see that module's own "GH-49 / issue #49, AC6" section) because it
extends that module's existing `engines.node`-vs-dependency contract to a
transitive dependency (`vite`), rather than introducing a new contract; AC7
and AC8 need no new tests at all, because the matrix- and setup-node-version
guards `test_frontend_node_version_pinning.py` already has (issue #17) cover
them unchanged, regardless of which Node-tooling major versions are locked.
This module is kept separate from `test_frontend_node_version_pinning.py`
rather than folding into it, because its contract is different in kind: that
module is about a single declared value (`engines.node`) staying internally
consistent across three files; this one is about two `devDependencies`
entries and their locked, installed counterparts staying consistent with
*each other* (a peer-dependency exactness requirement) and a transform-engine
config key migrating from one name to another -- none of which is a Node
*version* range at all.

-- What issue #49 actually is --

`vitest` and `@vitest/coverage-v8` are locked at `2.1.9` (both), pinned in
`frontend/package.json` as `^2.1.8` (both), measured at authoring time via
`frontend/package-lock.json`'s `packages["node_modules/vitest"].version` /
`packages["node_modules/@vitest/coverage-v8"].version`. A CRITICAL-severity
advisory against `vitest`'s `--ui`/`@vitest/ui` code path motivates bumping
past it; `4.1.11` is the target version this module's tests pin toward
(`npm view vitest@4.1.11 engines` and `npm view vitest@4.1.11
dependencies.vite` were both run at authoring time to confirm the exact
values named in each test below).

-- Why AC1 checks `package.json`'s *spec strings*, separately from AC2's
check of `package-lock.json`'s *locked versions* --

A `package.json` spec (e.g. `^4.1.11`) declares a *range* a maintainer
allows; `package-lock.json` records the *exact version* `npm ci` actually
installs from that range. These can drift independently: editing only
`package.json` without running `npm install`/`npm ci` to refresh the lockfile
leaves the range bumped but the locked version untouched (or vice versa, a
lockfile edited by hand without updating the range it was resolved from).
Testing both, from the two separate files that record them, catches either
half of that drift on its own -- exactly the same reasoning
`test_frontend_node_version_pinning.py`'s own docstring gives for reading
`engines.node` from `package-lock.json` rather than `node_modules`: this
module's `python` CI job never runs `npm ci` either, so `package-lock.json`
is the only place a locked version can be read from deterministically here.

-- Why AC1 and AC2 both additionally require the *pair* of specs/versions to
be identical to each other, not just individually "some 4.x.y" --

`npm view @vitest/coverage-v8@4.1.11 peerDependencies` (run at authoring
time) reports `{'vitest': '4.1.11', '@vitest/browser': '4.1.11'}` --
`@vitest/coverage-v8`'s peer dependency on `vitest` is pinned to an *exact*
version, not a range, for its major-4 line. If `vitest` and
`@vitest/coverage-v8` were bumped to two different 4.x.y patches (e.g.
`vitest@4.1.11` alongside `@vitest/coverage-v8@4.1.12`), `npm ci` fails on an
unsatisfiable peer dependency the moment either package's own patch drifts
from the other's -- so "both are some 4.x.y" alone is not sufficient; they
must be the exact same 4.x.y.

-- Why AC3 is a negative control, and what makes a negative control here
meaningfully different from a test that is trivially green because it checks
nothing --

`@vitest/ui` is not declared anywhere in `frontend/package.json` today, and
is (measured at authoring time) absent from `frontend/package-lock.json`'s
`packages` map entirely -- so `test_frontend_package_lock_does_not_install_vitest_ui`
below is already green *before* issue #49's fix lands, and stays green
*after* it too. It is not a vacuous check: the CRITICAL-severity advisory
motivating this bump concerns `vitest`'s `--ui` flag / the `@vitest/ui`
package specifically, and a major-version bump is exactly the kind of change
that can pull in a new transitive dependency by accident (a resolver
picking up a peer-optional package, a copy-pasted `package.json` snippet from
an upgrade guide that includes `@vitest/ui` alongside `vitest`, etc.). This
test's job is to keep that from happening silently -- it protects a "stays
false" invariant, which is exactly what a negative control is for, not a gap
in this module's red/green coverage.

-- Why AC9's check reads `frontend/vitest.config.ts` as text instead of
importing/evaluating it --

Same reasoning `tests/test_frontend_vitest_globals_typecheck.py`'s own
`_load_vitest_config_globals` gives for its `globals: true|false` regex:
`vitest.config.ts` is TypeScript, not JSON/YAML, and evaluating a
`defineConfig({...})` call would need a Node.js runtime this module's `python`
CI job never provisions. Unlike that module's single scalar-valued `globals:`
key, however, AC9 asks about *which top-level keys exist* in a multi-line
object literal, where a same-named key could legitimately appear again,
nested, deeper inside (e.g. a hypothetical `test: { esbuild: ... }`) without
that meaning what AC9 cares about. A single regex anchored on the key name
alone (`\\besbuild\\s*:` anywhere in the file) cannot tell those two positions
apart; `_top_level_defineconfig_keys` below tracks `{`/`}` brace depth across
the object literal's own lines instead, so a key is only counted when it
sits at the object literal's own top level. This is a deliberately narrower
problem than the one issue #32 documents for TSX/arrow-function detection
(see the "AC14" note issue #49's planning discussion raised and this module's
author declined to add a test for, in the git history around this commit):
brace-depth counting over a plain, non-JSX TypeScript object literal with no
braces inside its string literals is unambiguous, where distinguishing arrow
functions from regular functions in JSX source is a genuinely
syntax-sensitive problem no regex (and no dependency-graph-available parser)
reliably solves. `frontend/vitest.config.ts` contains no such string, and no
nested code block that itself contains unbalanced braces, at authoring time.

-- Why this module never runs `npm ci` or a live `npm view` --

Every `npm view` invocation named in this docstring and in individual tests'
docstrings below was run once, manually, at authoring time, to record real
published-package facts (a version's `engines`, its `dependencies.vite`
range, or `@vitest/coverage-v8`'s `peerDependencies`) as evidence for why
each assertion is the right one to make -- never as something a test itself
executes. `conftest.py`'s `block_outbound_http` fixture blocks `httpx`/
`requests` at the transport layer (not `npm`/subprocess calls), but a test
that shelled out to `npm view` at collection or run time would still be
non-deterministic (registry state can change between CI runs) and would
still need real network access unavailable to `.github/workflows/test.yml`'s
`python` job -- so every test below reads only files already committed to
this repository.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PACKAGE_JSON = REPO_ROOT / "frontend" / "package.json"
FRONTEND_PACKAGE_LOCK = REPO_ROOT / "frontend" / "package-lock.json"
VITEST_CONFIG_PATH = REPO_ROOT / "frontend" / "vitest.config.ts"

# The two packages issue #49 bumps together, and whose specs/locked versions
# must stay pairwise identical (see the module docstring's peer-dependency
# section for why).
_PINNED_PACKAGES: tuple[str, ...] = ("vitest", "@vitest/coverage-v8")


def _read_frontend_package_json() -> dict:
    return json.loads(FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8"))


def _read_frontend_package_lock() -> dict:
    return json.loads(FRONTEND_PACKAGE_LOCK.read_text(encoding="utf-8"))


def _devdependency_spec(package_json: dict, name: str) -> str | None:
    """Return `name`'s spec string from `package_json`'s `devDependencies`,
    or `None` if `name` is not declared there at all."""
    return package_json.get("devDependencies", {}).get(name)


def _locked_version(package_lock: dict, name: str) -> str | None:
    """Return `name`'s locked version, as recorded in `package_lock`'s
    `packages["node_modules/<name>"].version`, or `None` if `package_lock`
    has no such entry at all (distinct from the entry existing but recording
    no `version`, which would be a malformed lockfile and is treated the
    same way here: `None`, since a caller cannot act on either case)."""
    entry = package_lock.get("packages", {}).get(f"node_modules/{name}")
    if entry is None:
        return None
    return entry.get("version")


# --- AC1: package.json pins vitest and @vitest/coverage-v8 to identical ----
# --- ^4.X.Y specs ------------------------------------------------------------

_FULL_CARET_FOUR_RE = re.compile(r"^\^4\.\d+\.\d+$")


def _is_full_caret_four_spec(spec: str) -> bool:
    """Return whether `spec` is a caret range pinning an exact major-4
    version with a full `X.Y.Z` (e.g. `^4.1.11`) -- not a bare `^4`, not a
    partial `^4.1`, not a non-caret spec, not a different major, not a
    pre-release/build-tagged version, and not a `||`-alternation. Issue #49
    bumps `vitest`/`@vitest/coverage-v8` to exactly this shape
    (`^4.1.11`, confirmed via `npm view vitest@4.1.11 version` returning
    the plain `4.1.11` at authoring time, with no pre-release tag)."""
    return bool(_FULL_CARET_FOUR_RE.match(spec))


@pytest.mark.parametrize("package_name", _PINNED_PACKAGES)
def test_frontend_package_json_pins_package_to_a_full_caret_four_spec(package_name: str) -> None:
    """Given `frontend/package.json`'s `devDependencies`, when
    `package_name`'s declared spec is read, then it must be present and
    match `^4.X.Y` with a full major.minor.patch (issue #49, AC1) -- the
    current `^2.1.8`, a bare `^4`/`^4.1`, or a non-caret spec must all be
    rejected, so a partial or forgotten bump is not mistaken for a completed
    one.

    Does not cover: whether the version `npm ci` actually *locks* for this
    spec starts with `4.` -- see
    `test_frontend_package_lock_locks_package_to_a_major_version_four`
    below, which reads `package-lock.json` instead, since a `package.json`
    spec range alone never proves what got installed.
    """
    package_json = _read_frontend_package_json()
    spec = _devdependency_spec(package_json, package_name)
    assert spec is not None, (
        f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)} has no devDependencies entry for "
        f"{package_name!r}."
    )
    assert _is_full_caret_four_spec(spec), (
        f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)} pins {package_name!r} to {spec!r}, "
        "which does not match '^4.X.Y' with a full major.minor.patch (issue #49 bumps "
        "vitest and @vitest/coverage-v8 from ^2.1.8 to ^4.1.11)."
    )


def test_frontend_package_json_pins_vitest_and_coverage_v8_to_identical_specs() -> None:
    """Given `frontend/package.json`'s `devDependencies` entries for
    `vitest` and `@vitest/coverage-v8`, when both specs are read, then they
    must be exactly identical strings (issue #49, AC1) --
    `@vitest/coverage-v8@4`'s own `peerDependencies` pins `vitest` to an
    *exact* version (confirmed via `npm view @vitest/coverage-v8@4.1.11
    peerDependencies` returning `{'vitest': '4.1.11', ...}` at authoring
    time, not a range), so even two specs that each independently satisfy
    `_is_full_caret_four_spec` could still resolve to two different patches
    and break `npm ci`'s peer-dependency resolution.

    Does not cover: whether either spec, on its own, is shaped like
    `^4.X.Y` at all -- see
    `test_frontend_package_json_pins_package_to_a_full_caret_four_spec`
    above for that; this test only compares the two to each other."""
    package_json = _read_frontend_package_json()
    specs = {name: _devdependency_spec(package_json, name) for name in _PINNED_PACKAGES}
    assert all(spec is not None for spec in specs.values()), (
        f"expected {FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)}'s devDependencies to "
        f"declare both of {_PINNED_PACKAGES}; found {specs!r}"
    )
    vitest_spec, coverage_spec = specs["vitest"], specs["@vitest/coverage-v8"]
    assert vitest_spec == coverage_spec, (
        f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)} pins vitest to {vitest_spec!r} and "
        f"@vitest/coverage-v8 to {coverage_spec!r}; these must be identical because "
        "@vitest/coverage-v8@4's peerDependencies requires vitest at an exact matching "
        "version, not a range (verified via `npm view @vitest/coverage-v8@4.1.11 "
        "peerDependencies` at authoring time)."
    )


# --- Synthetic self-tests: _is_full_caret_four_spec -------------------------

_FULL_CARET_FOUR_CASES: dict[str, tuple[str, bool]] = {
    "exact_target_version": ("^4.1.11", True),
    "another_full_major_four_version": ("^4.0.0", True),
    "multi_digit_minor_and_patch": ("^4.12.345", True),
    "bare_major_only": ("^4", False),
    "major_minor_no_patch": ("^4.1", False),
    "no_caret_prefix": ("4.1.11", False),
    "tilde_not_caret": ("~4.1.11", False),
    "wrong_major_two": ("^2.1.8", False),
    "wrong_major_three": ("^3.9.9", False),
    # A multi-digit major beginning with the digit 4 (e.g. a hypothetical
    # future major 40) must not be mistaken for major 4: the character
    # immediately after '4' has to be '.', not another digit.
    "multi_digit_major_starting_with_four": ("^40.1.11", False),
    "prerelease_tag_rejected": ("^4.1.11-beta.0", False),
    "alternation_rejected": ("^4.1.11 || ^5.0.0", False),
}


@pytest.mark.parametrize("case_id", sorted(_FULL_CARET_FOUR_CASES))
def test_is_full_caret_four_spec_classifies_synthetic_specs_correctly(case_id: str) -> None:
    """Given synthetic spec strings covering the exact target shape, another
    valid major-4 full version, a multi-digit minor/patch, and every
    rejected shape this module's AC1 tests rely on being rejected (bare
    major, major.minor, non-caret, tilde, wrong major, a multi-digit major
    that merely starts with the digit 4, a pre-release tag, and a `||`
    alternation), when each is classified, then the result must match
    exactly what is expected -- proving the detector neither false-positives
    on a look-alike spec nor false-negatives on a genuinely valid one."""
    spec, expected = _FULL_CARET_FOUR_CASES[case_id]
    assert _is_full_caret_four_spec(spec) is expected


# --- AC2: package-lock.json locks vitest and @vitest/coverage-v8 to --------
# --- identical major-4 versions ----------------------------------------------


@pytest.mark.parametrize("package_name", _PINNED_PACKAGES)
def test_frontend_package_lock_locks_package_to_a_major_version_four(package_name: str) -> None:
    """Given `frontend/package-lock.json`'s
    `packages["node_modules/<package_name>"]` entry, when its `version` is
    read, then it must be present and start with `"4."` (issue #49, AC2) --
    the locked version, not the `package.json` spec range that resolved to
    it (see the module docstring for why both are checked separately).

    Does not cover: whether `package.json`'s own spec for the same package
    is itself shaped like `^4.X.Y` -- see
    `test_frontend_package_json_pins_package_to_a_full_caret_four_spec`
    above for that half."""
    package_lock = _read_frontend_package_lock()
    version = _locked_version(package_lock, package_name)
    assert version is not None, (
        f"{FRONTEND_PACKAGE_LOCK.relative_to(REPO_ROOT)} has no "
        f"packages['node_modules/{package_name}'].version entry."
    )
    assert version.startswith("4."), (
        f"{FRONTEND_PACKAGE_LOCK.relative_to(REPO_ROOT)} locks {package_name!r} to version "
        f"{version!r}, which does not start with '4.' (issue #49 bumps vitest and "
        "@vitest/coverage-v8 to ^4.1.11)."
    )


def test_frontend_package_lock_locks_vitest_and_coverage_v8_to_identical_versions() -> None:
    """Given `frontend/package-lock.json`'s locked versions for `vitest` and
    `@vitest/coverage-v8`, when both are read, then they must be exactly
    identical (issue #49, AC2) -- `@vitest/coverage-v8@4`'s peer dependency
    on `vitest` is pinned to an exact version (see the module docstring), so
    `npm ci` fails the moment the two locked versions diverge, even if both
    individually start with `4.`.

    Does not cover: whether either locked version, on its own, starts with
    `4.` -- see
    `test_frontend_package_lock_locks_package_to_a_major_version_four` above
    for that; this test only compares the two to each other."""
    package_lock = _read_frontend_package_lock()
    versions = {name: _locked_version(package_lock, name) for name in _PINNED_PACKAGES}
    assert all(v is not None for v in versions.values()), (
        f"expected {FRONTEND_PACKAGE_LOCK.relative_to(REPO_ROOT)} to lock both of "
        f"{_PINNED_PACKAGES}; found {versions!r}"
    )
    vitest_version, coverage_version = versions["vitest"], versions["@vitest/coverage-v8"]
    assert vitest_version == coverage_version, (
        f"{FRONTEND_PACKAGE_LOCK.relative_to(REPO_ROOT)} locks vitest to "
        f"{vitest_version!r} and @vitest/coverage-v8 to {coverage_version!r}; these must "
        "be identical because @vitest/coverage-v8@4's peerDependencies requires vitest at "
        "an exact matching version, not a range."
    )


# --- AC3: negative control -- @vitest/ui must not be installed --------------


def test_frontend_package_lock_does_not_install_vitest_ui() -> None:
    """Given `frontend/package-lock.json`, when it is checked for a
    `packages["node_modules/@vitest/ui"]` entry, then none must exist
    (issue #49, AC3). See the module docstring's "-- Why AC3 is a negative
    control --" section for why this stays green both before and after
    issue #49's fix, and why that is the correct behavior for this test
    rather than a gap in coverage: the CRITICAL-severity advisory motivating
    this bump concerns `vitest`'s `--ui` flag / the `@vitest/ui` package
    specifically, and this guard exists to keep a major-version bump from
    pulling it in as an accidental side effect.

    Does not cover: whether some other, differently-named package could
    reintroduce equivalent vulnerable code under a different package name --
    only the exact package name (`@vitest/ui`) the advisory names."""
    package_lock = _read_frontend_package_lock()
    assert "node_modules/@vitest/ui" not in package_lock.get("packages", {}), (
        f"{FRONTEND_PACKAGE_LOCK.relative_to(REPO_ROOT)} unexpectedly declares "
        "packages['node_modules/@vitest/ui']; issue #49's bump must not introduce it "
        "(the CRITICAL-severity advisory motivating this bump concerns @vitest/ui "
        "specifically)."
    )


# --- AC9: vitest.config.ts declares a top-level `oxc:` key, no top-level ---
# --- `esbuild:` key -----------------------------------------------------------
#
# Vitest re-exports Vite's `UserConfig` type from `vitest/config`. Vite 8
# (`vitest@4.1.11`'s own `dependencies.vite` range, `^6.0.0 || ^7.0.0 ||
# ^8.0.0`, resolves to `vite@8.2.2` today per `npm view vite version` at
# authoring time) deprecates its top-level `esbuild` transform option in
# favor of a new top-level `oxc` option: `vite@8.2.2`'s own
# `dist/node/index.d.ts`, inspected at authoring time via `npm pack
# vite@8.2.2` and extracting the tarball, reads:
#
#     /**
#      * Transform options to pass to esbuild.
#      * Or set to `false` to disable esbuild.
#      *
#      * @deprecated Use `oxc` option instead.
#      */
#     esbuild?: ESBuildOptions | false;
#     /**
#      * Transform options to pass to Oxc.
#      * Or set to `false` to disable Oxc.
#      */
#     oxc?: OxcOptions | false;
#
# both declared as direct sibling keys of `resolve`/`css`/`json` etc. on
# Vite's `UserConfig` interface -- i.e. both are top-level keys of the same
# object literal `frontend/vitest.config.ts`'s `defineConfig({...})` call
# already passes `esbuild: { jsx: "automatic" }` into today.


def _find_define_config_object_text(text: str) -> str:
    """Return the substring of `text` between the opening `{` of the object
    literal passed to `defineConfig({...})` and its matching closing `}`
    (both braces excluded). Tracks `{`/`}` depth from that opening brace
    onward so nested object literals (e.g. `resolve: { alias: {...} }`)
    inside `defineConfig`'s argument do not end the scan early. Raises
    `ValueError` if no `defineConfig({` call is found, or if the opening
    brace it finds has no matching closing brace before `text` ends."""
    call_match = re.search(r"defineConfig\s*\(\s*\{", text)
    if not call_match:
        raise ValueError("no 'defineConfig({' call found")
    start = call_match.end()
    depth = 1
    index = start
    while index < len(text):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index]
        index += 1
    raise ValueError("'defineConfig({' call's opening brace has no matching closing brace")


_TOP_LEVEL_KEY_RE = re.compile(r"^\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*:")


def _top_level_defineconfig_keys(text: str) -> set[str]:
    """Return the set of key names declared at the top level of the object
    literal passed to `defineConfig({...})` in `text` -- i.e. keys that are
    not nested inside another object (like a hypothetical `test: { esbuild:
    ... } }`). Tracks `{`/`}` brace depth line by line (a key is only
    counted when the object literal's brace depth is `0` *before* that
    line's own braces are counted), so a same-named key one level deeper is
    never mistaken for a top-level one, and this does not depend on any
    particular indentation style (a key and its opening brace on the same
    line, e.g. `oxc: { jsx: "automatic" },`, is still counted correctly,
    since the key is matched before that line's braces update the depth).

    Does not cover: two keys declared on the same source line (e.g.
    `esbuild: {}, oxc: {},`) -- only the first would be matched, since the
    key regex anchors on line-start. `frontend/vitest.config.ts` is a small,
    hand-authored, prettier-formatted file with one key per line at
    authoring time, so this is not a real-world gap here, only a documented
    boundary of what this helper checks. Raises `ValueError` (propagated
    from `_find_define_config_object_text`) under the same conditions that
    function raises it."""
    body = _find_define_config_object_text(text)
    keys: set[str] = set()
    depth = 0
    for line in body.splitlines():
        if depth == 0:
            match = _TOP_LEVEL_KEY_RE.match(line)
            if match:
                keys.add(match.group(1))
        depth += line.count("{") - line.count("}")
    return keys


def test_frontend_vitest_config_declares_oxc_and_not_esbuild_at_top_level() -> None:
    """Given `frontend/vitest.config.ts`, when the top-level keys of the
    object literal passed to `defineConfig({...})` are read, then the set
    must include `oxc` and must not include `esbuild` (issue #49, AC9) --
    see the section above this test for why Vite 8 (which `vitest@4.1.11`
    depends on) deprecates the latter in favor of the former, both as
    top-level `UserConfig` keys.

    Does not cover: whether `oxc`'s *value* (e.g. an equivalent to today's
    `jsx: "automatic"`) is itself correct, or whether the JSX transform
    actually still works -- only that the top-level key migration happened.
    Gate 4's own `npm test` run is what proves the transform still works in
    practice."""
    text = VITEST_CONFIG_PATH.read_text(encoding="utf-8")
    try:
        keys = _top_level_defineconfig_keys(text)
    except ValueError as exc:
        pytest.fail(f"{VITEST_CONFIG_PATH.relative_to(REPO_ROOT)}: {exc}")

    assert "oxc" in keys, (
        f"{VITEST_CONFIG_PATH.relative_to(REPO_ROOT)}'s defineConfig({{...}}) call has no "
        f"top-level 'oxc' key (found top-level keys: {sorted(keys)}). Vite 8's top-level "
        "'esbuild' option is deprecated in favor of 'oxc' (see the module's AC9 section)."
    )
    assert "esbuild" not in keys, (
        f"{VITEST_CONFIG_PATH.relative_to(REPO_ROOT)}'s defineConfig({{...}}) call still has "
        f"a top-level 'esbuild' key (found top-level keys: {sorted(keys)}), which Vite 8 "
        "deprecates in favor of 'oxc'."
    )


# --- Synthetic self-tests: _find_define_config_object_text ------------------


def test_find_define_config_object_text_returns_the_bracketed_contents() -> None:
    """Given a synthetic `defineConfig({...})` call whose object literal
    contains a nested object, when the call's contents are extracted, then
    exactly the text between the outer braces (exclusive) must be
    returned."""
    text = "export default defineConfig({\n  a: 1,\n  b: { c: 2 },\n});\n"
    extracted = _find_define_config_object_text(text)
    assert extracted == "\n  a: 1,\n  b: { c: 2 },\n"


def test_find_define_config_object_text_raises_when_no_call_is_found() -> None:
    """Given text with no `defineConfig(` call at all, when its contents are
    extracted, then a `ValueError` must be raised rather than silently
    returning an empty or nonsensical string."""
    with pytest.raises(ValueError, match="no 'defineConfig"):
        _find_define_config_object_text("export default {};\n")


def test_find_define_config_object_text_raises_on_an_unmatched_opening_brace() -> None:
    """Given a synthetic `defineConfig({...` call whose opening brace is
    never closed, when its contents are extracted, then a `ValueError` must
    be raised rather than scanning past the end of the text or returning a
    truncated result silently."""
    with pytest.raises(ValueError, match="no matching closing brace"):
        _find_define_config_object_text("defineConfig({\n  a: 1,\n")


# --- Synthetic self-tests: _top_level_defineconfig_keys ---------------------


def test_top_level_defineconfig_keys_returns_only_the_outermost_keys() -> None:
    """Given a synthetic `defineConfig({...})` call with keys nested at two
    levels deep, when its top-level keys are read, then only the truly
    top-level keys must be returned -- not `alias`, nested one level inside
    `resolve`, and not `c`, nested two levels inside `b`."""
    text = (
        "export default defineConfig({\n"
        "  resolve: {\n"
        "    alias: { '@': './src' },\n"
        "  },\n"
        "  a: 1,\n"
        "  b: {\n"
        "    c: {\n"
        "      d: 2,\n"
        "    },\n"
        "  },\n"
        "});\n"
    )
    assert _top_level_defineconfig_keys(text) == {"resolve", "a", "b"}


def test_top_level_defineconfig_keys_does_not_mistake_a_nested_same_name_key_for_top_level() -> (
    None
):
    """Given a synthetic `defineConfig({...})` call whose only appearance of
    the key name `esbuild` is nested inside `test: {...}` (never at the
    object literal's own top level), when top-level keys are read, then
    `esbuild` must NOT be reported as a top-level key -- the exact
    false-positive `_top_level_defineconfig_keys` exists to avoid, which a
    single unanchored `\\besbuild\\s*:` regex over the whole file would not
    have avoided."""
    text = "export default defineConfig({\n  test: {\n    esbuild: true,\n  },\n  oxc: {},\n});\n"
    keys = _top_level_defineconfig_keys(text)
    assert "esbuild" not in keys
    assert keys == {"test", "oxc"}


def test_top_level_defineconfig_keys_handles_a_key_and_its_brace_on_one_line() -> None:
    """Given a synthetic `defineConfig({...})` call where a key's opening
    and closing braces sit on the same source line as the key itself, when
    top-level keys are read, then that key must still be recognized as
    top-level (proving depth tracking does not require a key's value to
    start on its own line)."""
    text = 'defineConfig({\n  oxc: { jsx: "automatic" },\n  test: {},\n});\n'
    assert _top_level_defineconfig_keys(text) == {"oxc", "test"}
