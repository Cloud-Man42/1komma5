"""Tests for the frontend's Node.js version being pinned, and that pin being
internally consistent (GH-16).

GH-16 was opened because `frontend/package.json` declared no `engines.node`,
no `.nvmrc` existed at the repository root or under `frontend/`, and
`.github/workflows/test.yml`'s `frontend` job hard-coded `node-version: "20"`
with nothing tying that number to anything the frontend actually requires.
That gap between what CI ran (Node 20) and what a contributor's machine
happened to run is exactly how GH-11 went undetected: Node 20 has no global
`localStorage`, so Vitest's jsdom polyfill silently stood in for it and the
suite passed, while Node 22+ exposes a real (behaviorally different) global
`localStorage` that the code under test was never exercised against in CI.
Pinning a single declared range and cross-checking every place that mentions
a Node version against it is what keeps the next version-sensitive bug from
repeating that path.

This module originally held three behavioral guards, one per acceptance
criterion:

1. `test_frontend_package_json_declares_a_node_engines_range` and
   `test_frontend_engines_node_is_compatible_with_dependency` (AC1):
   `frontend/package.json`'s `engines.node` must exist and must not claim
   support for any Node version a direct dependency's own `engines.node`
   excludes.
2. `test_nvmrc_declares_a_version_within_the_engines_node_span` (AC2): a
   `.nvmrc` must exist (at the repo root or under `frontend/`) and the
   version it names must fall inside `engines.node`'s span.
3. `test_ci_frontend_job_node_version_is_within_engines_node_span` (AC3)
   checked that `.github/workflows/test.yml`'s `frontend` job's single
   `actions/setup-node` `node-version` fell inside `engines.node`'s span.
   **GH-17 removes this test** and replaces it with
   `test_every_setup_node_step_in_the_workflow_requests_a_version_within_engines_node_span`
   (AC5) -- see the "GH-17: generalizing the single-version CI check above
   into a matrix-aware, whole-workflow check" section further down for why
   AC3's original test could not simply be left in place alongside AC5's.

None of these tests pin a specific version number. They pin *consistency*
between the three declarations (and the dependencies' own requirements), so
whichever concrete range GH-16's fix picks, these tests only fail if that
range is either absent or contradicts one of the other declarations.

-- Why `engines.node` (dependency side) is read from `package-lock.json`,
not `node_modules` --

`.github/workflows/test.yml`'s `python` job (which is what runs this file in
CI) never runs `npm ci`; only the `frontend` job does. Reading
`frontend/node_modules/*/package.json` would make this module pass or fail
depending on an installation step CI's Python job never performs, which is
the opposite of deterministic. `frontend/package-lock.json` (lockfileVersion
3) is committed to the repository and records each locked package's
`engines` field under `packages["node_modules/<name>"].engines`, so it gives
the same dependency-declared `engines.node` values `node_modules` would,
without depending on `npm ci` having run. This was cross-checked directly
against `frontend/node_modules/*/package.json` while writing this module and
the two agree for every direct dependency.

-- Why this module implements its own (deliberately partial) semver-range
subset check instead of using a library --

No Python package in this repository's locked dependency graph understands
npm's `engines.node` range syntax (that is a Node-ecosystem grammar; Python's
`packaging` module implements PEP 440 instead, which is a different,
incompatible grammar), and adding a new third-party dependency is out of
scope for a test-only change. `_parse_range_alternative` and
`_parse_version_token` below implement only the subset of npm's range
grammar actually present across every `engines.node` field measured in this
repository (`^X.Y.Z` with `X >= 1`, `>=X`/`>=X.Y`/`>=X.Y.Z`, and `||`
alternation) plus the bare `X`/`X.Y`/`X.Y.Z` version tokens `.nvmrc` and
`actions/setup-node`'s `node-version` use. They deliberately do **not**
implement tilde ranges, hyphen ranges, `x`/`*` wildcards, pre-release tags,
or `^0.y.z`'s special-cased bump rule -- an unsupported form raises
`ValueError` with a message naming exactly what was rejected, so an
out-of-scope range fails this module's tests loudly instead of being
silently (and possibly wrongly) evaluated. The interval-subset arithmetic
these functions implement (`_merge_intervals` / `_is_subset_of_union`) was
authored against, and its output cross-checked token-for-token against, the
real `semver` package's `semver.subset()` (present in
`frontend/node_modules/semver`, transitively, at authoring time) for every
dependency `engines.node` value measured in this repository plus a
deliberately gapped synthetic range (`^18.18.0 || ^19.8.0`, which excludes
`19.0.0`-`19.7.x`); every comparison agreed. `frontend/node_modules/semver`
is not a declared dependency of this repository, so it is not imported here
-- it served only as an authoring-time oracle.

-- Why `.github/workflows/test.yml` is parsed with PyYAML instead of a
hand-rolled regex --

`tests/test_makefile_collector_dev_directory.py` and
`tests/test_workspace_install.py` both scrape the Makefile and README.md
with regexes, and one of those regexes (guarding GH-12's Makefile fix) was
later found (GH-32) to miss a space-indented variant of the exact assignment
it was meant to catch. `.github/workflows/test.yml` is YAML, and PyYAML
(`pyyaml`) is present in this repository's `uv.lock` -- a transitive
dependency reachable via `uv sync --all-packages`, the exact install command
`.github/workflows/test.yml`'s own `python` job runs before executing this
suite -- so a real YAML parser is both available and deterministic here.
Using it instead of a hand-rolled regex on the workflow's raw text removes
an entire class of indentation/quoting-variant bugs like GH-32's by
construction, rather than by writing a more careful regex.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PACKAGE_JSON = REPO_ROOT / "frontend" / "package.json"
FRONTEND_PACKAGE_LOCK = REPO_ROOT / "frontend" / "package-lock.json"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "test.yml"
NVMRC_CANDIDATES = [REPO_ROOT / ".nvmrc", REPO_ROOT / "frontend" / ".nvmrc"]

# A normalized (major, minor, patch) triple with every component filled in
# (missing components default to 0).
Version = tuple[int, int, int]
# A half-open range [lo, hi) that a `engines.node`/`.nvmrc`/`node-version`
# value can denote. `hi is None` means "no upper bound".
Interval = tuple[Version, "Version | None"]

# Sentinel standing in for "no upper bound" during interval-merge arithmetic,
# chosen far beyond any real Node major version so it always sorts last.
_UNBOUNDED: Version = (1 << 30, 0, 0)


# --- Parsing: bare version tokens (.nvmrc, actions/setup-node node-version) -

_VERSION_TOKEN_RE = re.compile(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?$")


def _parse_version_token(token: str) -> Interval:
    """Parse a bare, optionally `v`-prefixed numeric version token (as used
    by `.nvmrc` and `actions/setup-node`'s `node-version`) with 1-3
    dot-separated components into the half-open interval it denotes: a fully
    specified `X.Y.Z` denotes the single version `[X.Y.Z, X.Y.(Z+1))`, `X.Y`
    denotes every patch of that minor (`[X.Y.0, X.(Y+1).0)`), and bare `X`
    denotes every version of that major (`[X.0.0, (X+1).0.0)`) -- matching
    how `actions/setup-node` resolves a bare major like `"20"` to the latest
    `20.y.z`. Raises `ValueError` for anything else (pre-release/build
    metadata, `x`/`*` wildcards, `lts/*` aliases): this function does not
    resolve aliases, so a `.nvmrc` or `node-version` spelled that way must be
    rewritten to a numeric version for these tests to evaluate it."""
    match = _VERSION_TOKEN_RE.match(token.strip())
    if not match:
        raise ValueError(
            f"{token!r} is not a supported bare 'X', 'X.Y', or 'X.Y.Z' version token "
            "(no pre-release/build metadata, 'x'/'*' wildcards, or alias names like "
            "'lts/*' are supported)."
        )
    major_s, minor_s, patch_s = match.groups()
    major = int(major_s)
    if minor_s is None:
        return (major, 0, 0), (major + 1, 0, 0)
    minor = int(minor_s)
    if patch_s is None:
        return (major, minor, 0), (major, minor + 1, 0)
    patch = int(patch_s)
    return (major, minor, patch), (major, minor, patch + 1)


# --- Parsing: engines.node-style range specs (`^X.Y.Z`, `>=X`, `A || B`) ---

_CARET_RE = re.compile(r"^\^(\d+)\.(\d+)\.(\d+)$")
_GTE_RE = re.compile(r"^>=\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?$")


def _parse_range_alternative(term: str) -> Interval:
    """Parse a single `||`-separated alternative of an `engines.node`-style
    range spec into the half-open interval it denotes. Supports `^X.Y.Z`
    with `X >= 1` (`>=X.Y.Z <(X+1).0.0`, i.e. the common, non-`0.x` caret
    rule) and `>=X`/`>=X.Y`/`>=X.Y.Z` (unbounded above). Raises `ValueError`
    for anything else, including `^0.y.z` (npm's caret rule bumps a
    different, non-major component for a `0.x` base; no `engines.node`
    field measured in this repository's dependency graph uses it, so it is
    intentionally not implemented) and any of `~`, hyphen ranges, `x`/`*`
    wildcards, or pre-release tags."""
    term = term.strip()
    caret_match = _CARET_RE.match(term)
    if caret_match:
        major, minor, patch = (int(group) for group in caret_match.groups())
        if major < 1:
            raise ValueError(
                f"{term!r} is a '0.x' caret range; npm's caret rule bumps a "
                "different, non-major component for those (^0.2.3 := >=0.2.3 <0.3.0, "
                "^0.0.3 := >=0.0.3 <0.0.4), which this test helper does not implement "
                "because no engines.node field measured in this repository needs it."
            )
        return (major, minor, patch), (major + 1, 0, 0)
    gte_match = _GTE_RE.match(term)
    if gte_match:
        major_s, minor_s, patch_s = gte_match.groups()
        major = int(major_s)
        minor = int(minor_s) if minor_s is not None else 0
        patch = int(patch_s) if patch_s is not None else 0
        return (major, minor, patch), None
    raise ValueError(
        f"{term!r} is not a supported engines.node range term. This test helper only "
        "understands caret ranges with a full 'X.Y.Z' and major>=1 (e.g. '^20.11.0') "
        "and '>=' ranges with 'X', 'X.Y', or 'X.Y.Z' (e.g. '>=20'), combined with '||'. "
        "It does not implement '~', hyphen ranges, 'x'/'*' wildcards, or pre-release "
        "tags, because none of those appear in any engines.node field measured in "
        "this repository."
    )


def parse_node_engines_range(spec: str) -> list[Interval]:
    """Parse a full `engines.node`-style range spec (one or more `||`
    -separated alternatives) into the list of half-open intervals it
    denotes. See `_parse_range_alternative` for exactly which range grammar
    is (and is not) supported."""
    return [_parse_range_alternative(term) for term in spec.split("||")]


# --- Interval algebra: is a candidate span covered by a union of spans? ----


def _merge_intervals(intervals: list[Interval]) -> list[tuple[Version, Version]]:
    """Merge a list of half-open intervals (`hi=None` meaning unbounded, sorted
    internally) into the minimal list of non-overlapping, non-adjacent
    intervals covering the same points."""
    normalized = sorted(
        ((lo, _UNBOUNDED if hi is None else hi) for lo, hi in intervals),
        key=lambda interval: interval[0],
    )
    merged: list[tuple[Version, Version]] = []
    for lo, hi in normalized:
        if merged and lo <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged


def _is_subset_of_union(candidate: Interval, domain: list[Interval]) -> bool:
    """Return whether every version `candidate` covers is also covered by at
    least one interval in `domain`'s union. Correct even when `domain`'s
    intervals are unsorted, overlapping, or contain a gap `candidate` does
    not span: a gap `candidate` never touches cannot make it a non-subset
    only a gap it spans can, and merging `domain` first before comparing
    covers both cases."""
    candidate_lo, candidate_hi = candidate[0], _UNBOUNDED if candidate[1] is None else candidate[1]
    return any(lo <= candidate_lo and candidate_hi <= hi for lo, hi in _merge_intervals(domain))


# --- Reading the repository's own manifests ---------------------------------


def _read_frontend_package_json() -> dict:
    return json.loads(FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8"))


def _read_frontend_package_lock() -> dict:
    return json.loads(FRONTEND_PACKAGE_LOCK.read_text(encoding="utf-8"))


def _direct_dependency_names(package_json: dict) -> list[str]:
    """Return the sorted union of `package_json`'s `dependencies` and
    `devDependencies` keys -- both count as "direct dependencies" for
    engines.node compatibility purposes, since dev tooling (e.g. `vitest`)
    also has to run under whichever Node version a contributor or CI uses."""
    names = set(package_json.get("dependencies", {})) | set(package_json.get("devDependencies", {}))
    return sorted(names)


def _dependency_engines_node(package_lock: dict, name: str) -> str | None:
    """Return `name`'s own declared `engines.node` as recorded in
    `package_lock`'s `packages["node_modules/<name>"].engines.node`, or
    `None` if that package declares no `engines.node` constraint at all (in
    which case it imposes no compatibility requirement)."""
    entry = package_lock.get("packages", {}).get(f"node_modules/{name}")
    if entry is None:
        return None
    return entry.get("engines", {}).get("node")


# Computed at collection time from files that exist today (package.json and
# package-lock.json both exist regardless of GH-16's fix; only their
# `engines.node` *content* is what this module is testing), so building this
# parametrization list never fails collection even before GH-16 is fixed.
_FRONTEND_PACKAGE_JSON_DATA = _read_frontend_package_json()
_FRONTEND_PACKAGE_LOCK_DATA = _read_frontend_package_lock()
_DIRECT_DEPENDENCY_NAMES = _direct_dependency_names(_FRONTEND_PACKAGE_JSON_DATA)
_CONSTRAINED_DEPENDENCY_ENGINES: dict[str, str] = {
    name: engines_node
    for name in _DIRECT_DEPENDENCY_NAMES
    if (engines_node := _dependency_engines_node(_FRONTEND_PACKAGE_LOCK_DATA, name)) is not None
}


# --- AC1: frontend/package.json declares engines.node compatible with deps -


def test_frontend_package_json_declares_a_node_engines_range() -> None:
    """Given `frontend/package.json`, when its `engines` field is read, then
    it must declare a non-empty `node` range spelled in a form this module's
    range parser understands (see the module docstring for exactly which
    forms that is)."""
    package_json = _read_frontend_package_json()
    engines_node = package_json.get("engines", {}).get("node")
    assert engines_node, (
        f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)} has no 'engines.node'. Declare "
        "one compatible with every direct dependency's own engines.node (see "
        "test_frontend_engines_node_is_compatible_with_dependency) instead of leaving "
        "the supported Node range implicit."
    )
    try:
        parse_node_engines_range(engines_node)
    except ValueError as exc:
        pytest.fail(
            f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)} declares engines.node="
            f"{engines_node!r}, which this test's range parser could not read: {exc}"
        )


@pytest.mark.parametrize(
    "dependency_name",
    sorted(_CONSTRAINED_DEPENDENCY_ENGINES),
)
def test_frontend_engines_node_is_compatible_with_dependency(dependency_name: str) -> None:
    """Given `frontend/package.json`'s declared `engines.node` and a direct
    dependency's own `engines.node` (read from `package-lock.json`), when
    the declared range is compared against the dependency's range, then the
    declared range must not claim support for any Node version the
    dependency's own `engines.node` excludes."""
    package_json = _read_frontend_package_json()
    own_spec = package_json.get("engines", {}).get("node")
    dependency_spec = _CONSTRAINED_DEPENDENCY_ENGINES[dependency_name]
    assert own_spec, (
        f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)} has no 'engines.node', so it "
        f"cannot be checked for compatibility with {dependency_name}'s own "
        f"engines.node ({dependency_spec!r})."
    )

    try:
        own_intervals = parse_node_engines_range(own_spec)
        dependency_intervals = parse_node_engines_range(dependency_spec)
    except ValueError as exc:
        pytest.fail(
            f"could not parse an engines.node range while checking {dependency_name}: {exc}"
        )

    uncovered = [
        interval
        for interval in own_intervals
        if not _is_subset_of_union(interval, dependency_intervals)
    ]
    assert not uncovered, (
        f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)} declares engines.node="
        f"{own_spec!r}, which claims support for Node versions {dependency_name}'s own "
        f"engines.node ({dependency_spec!r}) excludes."
    )


def test_constrained_dependency_parametrization_covers_next_and_vitest() -> None:
    """Given the parametrized guard above, when the set of direct
    dependencies it was built from is inspected, then it must include at
    least `next` and `vitest` -- the two dependencies GH-16's own measured
    data table names -- so a change to `package.json` or `package-lock.json`
    that accidentally emptied the parametrization would be caught here
    instead of the parametrized guard silently reporting no failures for
    dependencies it never saw."""
    assert {"next", "vitest"}.issubset(_CONSTRAINED_DEPENDENCY_ENGINES), (
        f"expected the constrained-dependency parametrization to include at least "
        f"'next' and 'vitest', found: {sorted(_CONSTRAINED_DEPENDENCY_ENGINES)}"
    )


# --- AC2: a .nvmrc exists and is within the engines.node span --------------


def _first_nvmrc_version_token(path: Path) -> str:
    """Return the first non-empty, non-comment (`#`-prefixed) line of a
    `.nvmrc`-shaped file, with any trailing `#...` comment on that line
    stripped. Raises `ValueError` if the file has no such line."""
    for line in path.read_text(encoding="utf-8").splitlines():
        candidate = line.split("#", 1)[0].strip()
        if candidate:
            return candidate
    raise ValueError(f"{path} has no non-empty, non-comment line to read a Node version from.")


def test_nvmrc_declares_a_version_within_the_engines_node_span() -> None:
    """Given the repository, when a `.nvmrc` is searched for at the
    repository root and under `frontend/`, then at least one must exist, and
    each one that exists must name a Node version that falls inside
    `frontend/package.json`'s declared `engines.node` span."""
    existing = [path for path in NVMRC_CANDIDATES if path.is_file()]
    assert existing, (
        "expected a '.nvmrc' at one of "
        f"{[str(p.relative_to(REPO_ROOT)) for p in NVMRC_CANDIDATES]}; found none."
    )

    package_json = _read_frontend_package_json()
    own_spec = package_json.get("engines", {}).get("node")
    assert own_spec, (
        f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)} has no 'engines.node', so "
        "'.nvmrc' cannot be checked for falling inside its span."
    )
    try:
        own_intervals = parse_node_engines_range(own_spec)
    except ValueError as exc:
        pytest.fail(f"could not parse engines.node={own_spec!r}: {exc}")

    for path in existing:
        try:
            token = _first_nvmrc_version_token(path)
            token_interval = _parse_version_token(token)
        except ValueError as exc:
            pytest.fail(f"{path.relative_to(REPO_ROOT)}: {exc}")

        assert _is_subset_of_union(token_interval, own_intervals), (
            f"{path.relative_to(REPO_ROOT)} names Node version {token!r}, which falls "
            f"outside the engines.node span declared in "
            f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)} ({own_spec!r})."
        )


# --- Step lookup: the frontend job's single actions/setup-node step --------
#
# `_frontend_setup_node_step` originally backed AC3's own real-world test
# (`test_ci_frontend_job_node_version_is_within_engines_node_span`, removed
# by GH-17 -- see the module docstring and the "GH-17: generalizing..."
# section below). It is kept, unchanged, because it is still correct and
# still needed: `test_frontend_job_setup_node_step_references_its_own_matrix_key`
# (AC7) uses it to find the exact step whose `node-version` must reference
# `strategy.matrix`, and `test_frontend_setup_node_step_finds_the_single_setup_node_step`
# / `test_frontend_setup_node_step_raises_on_missing_or_ambiguous_step` below
# remain its synthetic self-tests, carried forward per AC11.


def _frontend_setup_node_step(workflow_data: dict) -> dict:
    """Return the `frontend` job's single `actions/setup-node` step from a
    parsed workflow document. Raises `AssertionError` (via a plain `assert`,
    which pytest's assertion rewriting reports with a full comparison) if
    the `frontend` job is missing, or if it has zero or more than one
    `actions/setup-node` step."""
    frontend_job = workflow_data.get("jobs", {}).get("frontend")
    assert frontend_job is not None, "workflow has no 'frontend' job"
    steps = frontend_job.get("steps", [])
    setup_node_steps = [
        step for step in steps if str(step.get("uses", "")).startswith("actions/setup-node@")
    ]
    assert len(setup_node_steps) == 1, (
        f"expected exactly one 'actions/setup-node' step in the 'frontend' job, found "
        f"{len(setup_node_steps)}"
    )
    return setup_node_steps[0]


# --- Synthetic validation of the parsing/interval helpers themselves -------
#
# The tests above only ever exercise whichever engines.node/.nvmrc/node-version
# values this repository currently happens to contain. The cases below feed
# the parsing and subset-checking helpers synthetic inputs covering shapes
# the real files may never contain (a deliberately gapped range, a
# version that lies inside one alternative but not the union, unsupported
# syntax), so both the "no false negative" and "no false positive" behavior
# of the detector is verified directly -- and so that this module has, in
# addition to the real, repository-reading acceptance checks above, evidence
# that the same detector logic can also report success on its own terms.

_RANGE_PARSE_CASES: dict[str, str] = {
    "single_gte_full_version": ">=20.0.0",
    "single_gte_bare_major": ">=20",
    "single_gte_major_minor": ">=14.17",
    "single_caret_full_version": "^20.11.0",
    "alternation_of_caret_and_gte": "^18.18.0 || ^19.8.0 || >= 20.0.0",
}
_RANGE_PARSE_EXPECTED: dict[str, list[Interval]] = {
    "single_gte_full_version": [((20, 0, 0), None)],
    "single_gte_bare_major": [((20, 0, 0), None)],
    "single_gte_major_minor": [((14, 17, 0), None)],
    "single_caret_full_version": [((20, 11, 0), (21, 0, 0))],
    "alternation_of_caret_and_gte": [
        ((18, 18, 0), (19, 0, 0)),
        ((19, 8, 0), (20, 0, 0)),
        ((20, 0, 0), None),
    ],
}


@pytest.mark.parametrize("case_id", sorted(_RANGE_PARSE_CASES))
def test_parse_node_engines_range_classifies_synthetic_specs_correctly(case_id: str) -> None:
    """Given synthetic `engines.node`-style range specs covering a plain
    `>=` with a full version, a bare major, and a major.minor, a caret
    range, and a real `||` alternation (next's own measured spec), when each
    is parsed, then it must produce exactly the expected list of half-open
    intervals."""
    assert parse_node_engines_range(_RANGE_PARSE_CASES[case_id]) == _RANGE_PARSE_EXPECTED[case_id]


_UNSUPPORTED_RANGE_SPECS = [
    pytest.param("~20.11.0", id="tilde_range"),
    pytest.param("1.2.3 - 2.3.4", id="hyphen_range"),
    pytest.param("20.x", id="x_range"),
    pytest.param("*", id="wildcard"),
    pytest.param("^0.2.3", id="zero_x_caret"),
    pytest.param("20.0.0-rc.1", id="prerelease_tag"),
    pytest.param("not-a-version", id="garbage"),
]


@pytest.mark.parametrize("spec", _UNSUPPORTED_RANGE_SPECS)
def test_parse_node_engines_range_rejects_unsupported_syntax_loudly(spec: str) -> None:
    """Given a range spec written in a form this module's parser does not
    implement (tilde ranges, hyphen ranges, x-ranges, wildcards, `0.x`
    caret ranges, pre-release tags, or plain garbage), when it is parsed,
    then a `ValueError` naming the rejected term must be raised -- proving
    unsupported syntax fails loudly instead of being silently misjudged as
    compatible or incompatible."""
    with pytest.raises(ValueError, match=re.escape(spec)):
        parse_node_engines_range(spec)


_VERSION_TOKEN_CASES: dict[str, str] = {
    "bare_major": "20",
    "major_minor": "20.11",
    "major_minor_patch": "20.11.5",
    "v_prefixed": "v20.11.5",
}
_VERSION_TOKEN_EXPECTED: dict[str, Interval] = {
    "bare_major": ((20, 0, 0), (21, 0, 0)),
    "major_minor": ((20, 11, 0), (20, 12, 0)),
    "major_minor_patch": ((20, 11, 5), (20, 11, 6)),
    "v_prefixed": ((20, 11, 5), (20, 11, 6)),
}


@pytest.mark.parametrize("case_id", sorted(_VERSION_TOKEN_CASES))
def test_parse_version_token_classifies_synthetic_tokens_correctly(case_id: str) -> None:
    """Given synthetic bare version tokens covering a bare major, a
    major.minor, a full major.minor.patch, and a `v`-prefixed version, when
    each is parsed, then it must produce exactly the expected half-open
    interval."""
    assert _parse_version_token(_VERSION_TOKEN_CASES[case_id]) == _VERSION_TOKEN_EXPECTED[case_id]


@pytest.mark.parametrize(
    "token",
    [
        pytest.param("lts/iron", id="lts_alias"),
        pytest.param("20.11.0-rc.1", id="prerelease_tag"),
        pytest.param("", id="empty_string"),
        pytest.param("current", id="alias_word"),
    ],
)
def test_parse_version_token_rejects_unsupported_syntax_loudly(token: str) -> None:
    """Given a bare version token written in a form this module's parser
    does not resolve (an nvm alias name, a pre-release tag, or an empty
    string), when it is parsed, then a `ValueError` must be raised rather
    than the token being silently treated as version `0.0.0` or ignored."""
    with pytest.raises(ValueError):
        _parse_version_token(token)


# `(candidate spec, domain specs, expected)` -- domain built from multiple
# `||`-joined pieces where relevant, so `_is_subset_of_union` is exercised
# against a genuinely gapped union rather than only ever a single interval.
_SUBSET_CASES: dict[str, tuple[str, str, bool]] = {
    "candidate_fully_inside_unbounded_domain": (">=20.0.0", ">=18", True),
    "candidate_equal_to_domain_lower_bound": (">=20.0.0", ">=20.0.0", True),
    "candidate_below_domain_lower_bound_is_not_subset": (">=19.0.0", ">=20.0.0", False),
    # Domain has a real gap between 19.0.0 (exclusive) and 19.8.0: a
    # candidate spanning >=18.18.0 crosses that gap and is not a subset,
    # even though its lower bound sits inside the domain's first alternative.
    "candidate_spanning_a_domain_gap_is_not_subset": (
        ">=18.18.0",
        "^18.18.0 || ^19.8.0",
        False,
    ),
    # Same gapped domain, but a candidate that stays entirely within the
    # first alternative is still a subset.
    "candidate_inside_one_alternative_of_a_gapped_domain_is_subset": (
        "^18.18.0",
        "^18.18.0 || ^19.8.0",
        True,
    ),
    "candidate_matches_real_next_spec_is_subset_of_itself": (
        "^18.18.0 || ^19.8.0 || >= 20.0.0",
        "^18.18.0 || ^19.8.0 || >= 20.0.0",
        True,
    ),
}


@pytest.mark.parametrize("case_id", sorted(_SUBSET_CASES))
def test_is_subset_of_union_classifies_synthetic_ranges_correctly(case_id: str) -> None:
    """Given synthetic (candidate, domain) range pairs covering a candidate
    fully inside an unbounded domain, one exactly at the domain's lower
    bound, one entirely below it, one that spans a real gap in a
    multi-alternative domain, one that stays inside a single alternative of
    that same gapped domain, and a candidate identical to its domain, when
    each candidate interval is checked against the domain's parsed
    intervals, then the subset check must classify each exactly as
    expected -- proving the detector neither false-positives across a gap
    nor false-negatives on a genuinely-covered candidate. The gapped-domain
    cases were cross-checked against the real `semver` package's
    `semver.subset()` at authoring time (see the module docstring)."""
    candidate_spec, domain_spec, expected = _SUBSET_CASES[case_id]
    candidate_intervals = parse_node_engines_range(candidate_spec)
    domain_intervals = parse_node_engines_range(domain_spec)
    result = all(
        _is_subset_of_union(interval, domain_intervals) for interval in candidate_intervals
    )
    assert result is expected


# --- Synthetic validation of the .nvmrc line-reading helper ----------------


def test_first_nvmrc_version_token_skips_blank_lines_and_comments(tmp_path: Path) -> None:
    """Given a synthetic `.nvmrc` whose first lines are blank and a
    comment, when its first real version token is read, then the blank
    lines and comment must be skipped and the version token returned with
    any trailing inline comment stripped."""
    nvmrc = tmp_path / ".nvmrc"
    nvmrc.write_text("\n# use the LTS line\n20.11.0  # keep in sync with engines.node\n")
    assert _first_nvmrc_version_token(nvmrc) == "20.11.0"


def test_first_nvmrc_version_token_raises_on_a_file_with_no_content(tmp_path: Path) -> None:
    """Given a synthetic `.nvmrc` containing only blank lines and comments,
    when its first real version token is read, then a `ValueError` must be
    raised rather than an empty string being treated as a version."""
    nvmrc = tmp_path / ".nvmrc"
    nvmrc.write_text("\n# nothing but comments here\n\n")
    with pytest.raises(ValueError):
        _first_nvmrc_version_token(nvmrc)


# --- Synthetic validation of the workflow step-extraction helper -----------


def test_frontend_setup_node_step_finds_the_single_setup_node_step() -> None:
    """Given a synthetic workflow document shaped like
    `.github/workflows/test.yml` (a `frontend` job with an
    `actions/setup-node` step among others), when its `actions/setup-node`
    step is extracted, then the correct step (and only that step) must be
    returned."""
    workflow_data = {
        "jobs": {
            "frontend": {
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"uses": "actions/setup-node@v4", "with": {"node-version": "20"}},
                    {"name": "Install frontend dependencies", "run": "npm ci"},
                ]
            }
        }
    }
    step = _frontend_setup_node_step(workflow_data)
    assert step == {"uses": "actions/setup-node@v4", "with": {"node-version": "20"}}


@pytest.mark.parametrize(
    "workflow_data",
    [
        pytest.param({"jobs": {}}, id="no_frontend_job"),
        pytest.param(
            {"jobs": {"frontend": {"steps": [{"uses": "actions/checkout@v4"}]}}},
            id="zero_setup_node_steps",
        ),
        pytest.param(
            {
                "jobs": {
                    "frontend": {
                        "steps": [
                            {"uses": "actions/setup-node@v4", "with": {"node-version": "20"}},
                            {"uses": "actions/setup-node@v4", "with": {"node-version": "22"}},
                        ]
                    }
                }
            },
            id="two_setup_node_steps",
        ),
    ],
)
def test_frontend_setup_node_step_raises_on_missing_or_ambiguous_step(workflow_data: dict) -> None:
    """Given a synthetic workflow document missing a `frontend` job, or
    whose `frontend` job has zero or two `actions/setup-node` steps, when
    its `actions/setup-node` step is extracted, then an `AssertionError`
    must be raised rather than silently picking a step or returning
    `None`."""
    with pytest.raises(AssertionError):
        _frontend_setup_node_step(workflow_data)


# --- Synthetic "would this detector pass?" scenarios ------------------------
#
# The AC1-3 tests above run against this repository's real manifests, so
# whether they pass depends entirely on what those manifests currently
# declare -- GH-16 was opened because none of them declared an engines.node
# at all. The cases below run the exact same parsing and subset-checking
# helpers against hand-built, internally-consistent inputs representative of
# what a fix could look like, proving the detector logic itself is capable
# of reporting success -- not only failure -- independent of any single
# repository state.


def test_synthetic_engines_node_pipeline_detects_a_compatible_declaration() -> None:
    """Given a synthetic package.json/package-lock.json pair shaped like the
    real ones, with a declared `engines.node` chosen to fall entirely
    within a dependency's own `engines.node`, when the same
    reading-and-subset-checking steps `test_frontend_engines_node_is_compatible_with_dependency`
    performs are run against them, then no incompatibility is reported."""
    package_json = {"dependencies": {"next": "^18.18.0 || ^19.8.0 || >= 20.0.0"}}
    package_lock = {
        "packages": {
            "node_modules/next": {"engines": {"node": "^18.18.0 || ^19.8.0 || >= 20.0.0"}},
        }
    }
    dependency_name = _direct_dependency_names(package_json)[0]
    dependency_spec = _dependency_engines_node(package_lock, dependency_name)
    assert dependency_spec is not None

    own_spec = ">=20.0.0"
    own_intervals = parse_node_engines_range(own_spec)
    dependency_intervals = parse_node_engines_range(dependency_spec)
    uncovered = [
        interval
        for interval in own_intervals
        if not _is_subset_of_union(interval, dependency_intervals)
    ]
    assert uncovered == []


def test_synthetic_engines_node_pipeline_detects_an_incompatible_declaration() -> None:
    """Given the same synthetic package.json/package-lock.json pair as
    above, but with a declared `engines.node` chosen to fall partly outside
    the dependency's own `engines.node` (next excludes 19.0.0-19.7.x, which
    `>=19.0.0` claims support for), when the same steps are run, then the
    incompatibility must be reported rather than missed."""
    package_json = {"dependencies": {"next": "^18.18.0 || ^19.8.0 || >= 20.0.0"}}
    package_lock = {
        "packages": {
            "node_modules/next": {"engines": {"node": "^18.18.0 || ^19.8.0 || >= 20.0.0"}},
        }
    }
    dependency_name = _direct_dependency_names(package_json)[0]
    dependency_spec = _dependency_engines_node(package_lock, dependency_name)
    assert dependency_spec is not None

    own_spec = ">=19.0.0"
    own_intervals = parse_node_engines_range(own_spec)
    dependency_intervals = parse_node_engines_range(dependency_spec)
    uncovered = [
        interval
        for interval in own_intervals
        if not _is_subset_of_union(interval, dependency_intervals)
    ]
    assert uncovered != []


def test_synthetic_nvmrc_and_ci_pipeline_detects_both_within_and_outside_span(
    tmp_path: Path,
) -> None:
    """Given a synthetic `engines.node` span, a synthetic `.nvmrc`, and a
    synthetic workflow document, when the same version-token parsing and
    subset-checking steps `test_nvmrc_declares_a_version_within_the_engines_node_span`
    performs, paired with `_frontend_setup_node_step`'s step lookup (the same
    lookup `test_frontend_job_setup_node_step_references_its_own_matrix_key`
    (AC7) uses), are run against a version inside the span and one outside
    it, then the in-span version must be reported compatible and the
    out-of-span one must be reported incompatible. GH-17 removed the
    real-world test that used to pair this same lookup with a subset check
    directly (`test_ci_frontend_job_node_version_is_within_engines_node_span`,
    AC3 -- see the module docstring); this synthetic case is kept because it
    validates the helper combination itself, independent of which real test
    currently exercises it."""
    own_intervals = parse_node_engines_range(">=20.0.0")

    nvmrc = tmp_path / ".nvmrc"
    nvmrc.write_text("20.11.0\n")
    in_span_token = _first_nvmrc_version_token(nvmrc)
    assert _is_subset_of_union(_parse_version_token(in_span_token), own_intervals)

    workflow_data = {
        "jobs": {
            "frontend": {
                "steps": [
                    {"uses": "actions/setup-node@v4", "with": {"node-version": "18"}},
                ]
            }
        }
    }
    out_of_span_step = _frontend_setup_node_step(workflow_data)
    out_of_span_version = str(out_of_span_step["with"]["node-version"])
    assert not _is_subset_of_union(_parse_version_token(out_of_span_version), own_intervals)


# =============================================================================
# GH-17: generalizing the single-version CI check above into a matrix-aware,
# whole-workflow check, and removing AC3's real-world test.
#
# GH-17 (issue #70's flakiness finding) splits the `frontend` job's single
# hard-coded `node-version` into a two-leg `strategy.matrix`, and adds a
# second job (`frontend-lint`) with its own `actions/setup-node` step.
#
# -- Removing AC3's real-world test, and why it could not just stay --
#
# `_frontend_setup_node_step`, AC1/AC2's tests, and `_frontend_setup_node_step`'s
# own synthetic self-tests (`test_frontend_setup_node_step_finds_the_single_setup_node_step`,
# `test_frontend_setup_node_step_raises_on_missing_or_ambiguous_step`) are
# left completely unchanged below -- `_frontend_setup_node_step` still looks
# up exactly the `frontend` job and still requires exactly one
# `actions/setup-node` step there, which remains true after GH-17's fix (the
# matrix parametrizes *runs* of that one YAML step, it does not add a second
# step to the job's `steps:` list). AC11 protects exactly that helper and
# that self-test family, and both are honored as-is.
#
# AC3's own *real-world* test, `test_ci_frontend_job_node_version_is_within_engines_node_span`,
# is different: it fed `_frontend_setup_node_step`'s raw `with.node-version`
# string straight into `_parse_version_token`, which understands numeric
# version tokens only. Once GH-17's fix lands, that string becomes the
# literal expression `${{ matrix.node }}` (or whatever key AC7 picks) --
# not a version. Verified directly against this module's own functions
# before deleting the test, by hand-injecting that exact future shape into a
# deep copy of the real, parsed workflow document:
#
#     >>> _parse_version_token("${{ matrix.node }}")
#     ValueError: '${{ matrix.node }}' is not a supported bare 'X', 'X.Y',
#     or 'X.Y.Z' version token (no pre-release/build metadata, 'x'/'*'
#     wildcards, or alias names like 'lts/*' are supported).
#
# `test_ci_frontend_job_node_version_is_within_engines_node_span` catches
# `ValueError` and turns it into `pytest.fail`, so it would have become a
# ninth red test after GH-17's fix -- one outside every acceptance
# criterion's contract, that Gate 4 could only silence by editing a test
# file, which is exactly what gate ordering exists to prevent. Deleting it
# here, rather than leaving it to fail for an unowned reason later, is what
# keeps the red set exactly the eight acceptance-criteria failures below.
#
# It is deleted, not merely edited to resolve the expression itself, because
# `test_every_setup_node_step_in_the_workflow_requests_a_version_within_engines_node_span`
# (AC5, below) already covers strictly more than it did: AC3's test read one
# step in one job and parsed its `node-version` as a literal; AC5's test
# reads every `actions/setup-node` step in the *whole* workflow (via
# `_all_setup_node_steps`) and, for each one, resolves a `${{ matrix.<key>
# }}` expression against that job's own `strategy.matrix` first (via
# `_node_version_candidates`) before parsing and subset-checking every
# concrete candidate version -- confirmed directly, against the same
# hand-injected future workflow state used above, that
# `_all_setup_node_steps` + `_node_version_candidates` resolve
# `${{ matrix.node }}` to `["20.9.0", "26.4.0"]` and parse both without
# error, where AC3's test raised. Every real (non-matrix) `node-version`
# AC3's test could ever have read (e.g. `frontend-lint`'s own literal
# `node-version`, once GH-17 adds that job) is still covered by AC5's test
# too, since `_node_version_candidates` returns a literal `with.node-version`
# unchanged when it is not a `${{ matrix.* }}` expression.
#
# Five new acceptance criteria, five new behavioral guards:
#
# 1. `test_every_setup_node_step_in_the_workflow_requests_a_version_within_engines_node_span`
#    (AC5): supersedes and replaces AC3's single-job, single-step check
#    (`test_ci_frontend_job_node_version_is_within_engines_node_span`,
#    removed above) with a whole-workflow check. A step whose `node-version`
#    is a `${{ matrix.<key> }}` expression is resolved against that job's
#    own `strategy.matrix.<key>` list (see `_node_version_candidates`)
#    rather than parsed as a literal token.
# 2. `test_frontend_job_setup_node_step_references_its_own_matrix_key`
#    (AC7): the `frontend` job's `strategy.matrix` must have exactly one key
#    mapped to a list, and its `actions/setup-node` step's `node-version`
#    must be the literal expression referencing that same key.
# 3. `test_every_frontend_matrix_entry_is_within_the_engines_node_span`
#    (AC8): every entry in that matrix list must itself fall inside
#    `frontend/package.json`'s declared `engines.node` span.
# 4. `test_frontend_matrix_entry_set_is_exactly_the_floor_and_the_nvmrc_entry`
#    (AC9): the matrix's entry *set* must be exactly two versions -- the one
#    whose parsed lower bound equals `engines.node`'s lowest lower bound
#    across its whole `||`-union, and the one that covers `.nvmrc`'s
#    declared version. Both are derived from the repository's own files at
#    test time, never hard-coded, per AC9's own requirement.
# 5. `test_frontend_job_strategy_has_fail_fast_disabled` (AC10):
#    `strategy.fail-fast` must be the boolean `False`.
# =============================================================================


# --- Parsing: resolving a `${{ matrix.<key> }}` node-version expression ----

_MATRIX_EXPR_RE = re.compile(r"^\$\{\{\s*matrix\.([A-Za-z0-9_-]+)\s*\}\}$")


def _frontend_job_matrix(workflow_data: dict) -> dict:
    """Return the `frontend` job's `strategy.matrix` dict from a parsed
    workflow document (an empty dict if the job has no `strategy` or no
    `matrix` key at all -- today's state, before GH-17's fix). Raises
    `AssertionError` if the `frontend` job itself is missing."""
    frontend_job = workflow_data.get("jobs", {}).get("frontend")
    assert frontend_job is not None, "workflow has no 'frontend' job"
    return frontend_job.get("strategy", {}).get("matrix", {})


def _matrix_key_and_versions(matrix: dict) -> tuple[str, list[str]]:
    """Return a `strategy.matrix` dict's single key and its list of values
    (stringified). Raises `AssertionError` if the matrix has zero keys, more
    than one key, or if the one key's value is not a non-empty list --
    exactly the shape AC7 requires (one matrix dimension, driving one
    `actions/setup-node` step's `node-version`)."""
    assert len(matrix) == 1, (
        f"expected exactly one strategy.matrix key, found {sorted(matrix)} (matrix={matrix!r})"
    )
    ((key, values),) = matrix.items()
    assert isinstance(values, list) and values, (
        f"expected strategy.matrix.{key} to be a non-empty list, got {values!r}"
    )
    return key, [str(value) for value in values]


def _all_setup_node_steps(workflow_data: dict) -> list[tuple[str, dict, dict]]:
    """Return every `actions/setup-node` step across every job in a parsed
    workflow document, as `(job_name, job, step)` triples, in
    dict-iteration (i.e. document) order.

    Unlike `_frontend_setup_node_step`, this scans the *whole* workflow and
    returns a list rather than asserting there is exactly one step overall
    -- GH-17 legitimately adds a second job (`frontend-lint`) with its own
    `actions/setup-node` step, so "exactly one across the whole workflow"
    would no longer hold once that job exists, even though it still holds
    for the `frontend` job alone. The `job` dict is returned alongside each
    step so a caller can resolve a `${{ matrix.<key> }}` `node-version`
    against that same job's own `strategy.matrix` (see
    `_node_version_candidates`)."""
    result: list[tuple[str, dict, dict]] = []
    for job_name, job in workflow_data.get("jobs", {}).items():
        for step in job.get("steps", []):
            if str(step.get("uses", "")).startswith("actions/setup-node@"):
                result.append((job_name, job, step))
    return result


def _node_version_candidates(job: dict, step: dict) -> list[str]:
    """Return the concrete `node-version` value(s) `step`'s
    `with.node-version` actually resolves to at workflow-run time: the
    literal string itself, or -- if it is a `${{ matrix.<key> }}`
    expression -- every entry in `job`'s `strategy.matrix.<key>` list.
    Raises `AssertionError` if the expression references a matrix key the
    job's `strategy.matrix` does not define, or whose value is not a list."""
    raw = str(step.get("with", {}).get("node-version", ""))
    matrix_match = _MATRIX_EXPR_RE.match(raw.strip())
    if not matrix_match:
        return [raw]

    key = matrix_match.group(1)
    matrix = job.get("strategy", {}).get("matrix", {})
    assert key in matrix, (
        f"step references '${{{{ matrix.{key} }}}}' but the job's strategy.matrix has no "
        f"{key!r} key; matrix keys found: {sorted(matrix)}"
    )
    values = matrix[key]
    assert isinstance(values, list), f"expected strategy.matrix.{key} to be a list, got {values!r}"
    return [str(value) for value in values]


def _lowest_lower_bound(intervals: list[Interval]) -> Version:
    """Return the smallest lower bound among a list of half-open intervals
    -- the version at which their union's coverage begins."""
    return min(lo for lo, _hi in intervals)


# --- Synthetic self-tests: _frontend_job_matrix -----------------------------


def test_frontend_job_matrix_returns_the_matrix_dict_when_present() -> None:
    """Given a synthetic workflow document whose `frontend` job declares a
    `strategy.matrix`, when it is read, then the exact matrix dict must be
    returned."""
    workflow_data = {
        "jobs": {"frontend": {"strategy": {"matrix": {"node_version": ["20.9.0", "26.4.0"]}}}}
    }
    assert _frontend_job_matrix(workflow_data) == {"node_version": ["20.9.0", "26.4.0"]}


@pytest.mark.parametrize(
    "workflow_data",
    [
        pytest.param({"jobs": {"frontend": {}}}, id="no_strategy_key"),
        pytest.param({"jobs": {"frontend": {"strategy": {}}}}, id="no_matrix_key"),
    ],
)
def test_frontend_job_matrix_returns_an_empty_dict_when_absent(workflow_data: dict) -> None:
    """Given a synthetic workflow document whose `frontend` job has no
    `strategy` at all, or a `strategy` with no `matrix` key, when it is
    read, then an empty dict must be returned rather than raising -- this is
    today's real, pre-GH-17 shape."""
    assert _frontend_job_matrix(workflow_data) == {}


def test_frontend_job_matrix_raises_when_the_frontend_job_is_missing() -> None:
    """Given a synthetic workflow document with no `frontend` job, when its
    matrix is requested, then an `AssertionError` must be raised."""
    with pytest.raises(AssertionError):
        _frontend_job_matrix({"jobs": {}})


# --- Synthetic self-tests: _matrix_key_and_versions -------------------------


def test_matrix_key_and_versions_returns_the_single_key_and_its_list() -> None:
    """Given a synthetic matrix dict with exactly one key mapped to a
    non-empty list, when it is read, then that key and a stringified copy
    of its list must be returned."""
    key, versions = _matrix_key_and_versions({"node_version": ["20.9.0", "26.4.0"]})
    assert key == "node_version"
    assert versions == ["20.9.0", "26.4.0"]


@pytest.mark.parametrize(
    "matrix",
    [
        pytest.param({}, id="zero_keys"),
        pytest.param({"a": ["1"], "b": ["2"]}, id="two_keys"),
        pytest.param({"node_version": "20.9.0"}, id="value_is_not_a_list"),
        pytest.param({"node_version": []}, id="value_is_an_empty_list"),
    ],
)
def test_matrix_key_and_versions_raises_on_malformed_matrices(matrix: dict) -> None:
    """Given a synthetic matrix dict with zero keys, two keys, a non-list
    value, or an empty-list value, when it is read, then an
    `AssertionError` must be raised rather than silently picking an
    arbitrary key or accepting a shape AC7 does not allow."""
    with pytest.raises(AssertionError):
        _matrix_key_and_versions(matrix)


# --- Synthetic self-tests: _all_setup_node_steps ----------------------------


def test_all_setup_node_steps_finds_a_step_in_every_job_that_has_one() -> None:
    """Given a synthetic workflow document with a `python` job (no
    `actions/setup-node` step), a `frontend` job (one such step), and a
    `frontend-lint` job (another such step), when every `actions/setup-node`
    step in the workflow is collected, then exactly the two real ones must
    be returned, each paired with its own job name and job dict."""
    workflow_data = {
        "jobs": {
            "python": {"steps": [{"uses": "actions/checkout@v5"}]},
            "frontend": {
                "steps": [{"uses": "actions/setup-node@v5", "with": {"node-version": "22"}}]
            },
            "frontend-lint": {
                "steps": [{"uses": "actions/setup-node@v5", "with": {"node-version": "26.4.0"}}]
            },
        }
    }
    found = _all_setup_node_steps(workflow_data)
    assert [(job_name, step["with"]["node-version"]) for job_name, _job, step in found] == [
        ("frontend", "22"),
        ("frontend-lint", "26.4.0"),
    ]


def test_all_setup_node_steps_returns_an_empty_list_when_none_exist() -> None:
    """Given a synthetic workflow document whose only job has no
    `actions/setup-node` step, when every such step is collected, then an
    empty list must be returned rather than raising."""
    workflow_data = {"jobs": {"python": {"steps": [{"uses": "actions/checkout@v5"}]}}}
    assert _all_setup_node_steps(workflow_data) == []


# --- Synthetic self-tests: _node_version_candidates -------------------------


def test_node_version_candidates_returns_the_literal_value_when_not_a_matrix_expression() -> None:
    """Given a synthetic job/step pair whose `node-version` is a plain
    literal (not a `${{ matrix.* }}` expression), when candidates are
    resolved, then a single-element list holding that literal must be
    returned."""
    job = {"steps": [{"uses": "actions/setup-node@v5", "with": {"node-version": "22"}}]}
    step = job["steps"][0]
    assert _node_version_candidates(job, step) == ["22"]


def test_node_version_candidates_resolves_a_matrix_expression_to_the_full_list() -> None:
    """Given a synthetic job whose `node-version` is `${{ matrix.node_version
    }}` and whose `strategy.matrix.node_version` is a two-entry list, when
    candidates are resolved, then both matrix entries must be returned."""
    job = {
        "strategy": {"matrix": {"node_version": ["20.9.0", "26.4.0"]}},
        "steps": [
            {
                "uses": "actions/setup-node@v5",
                "with": {"node-version": "${{ matrix.node_version }}"},
            }
        ],
    }
    step = job["steps"][0]
    assert _node_version_candidates(job, step) == ["20.9.0", "26.4.0"]


def test_node_version_candidates_raises_when_the_referenced_matrix_key_is_missing() -> None:
    """Given a synthetic job whose `node-version` references `${{
    matrix.node_version }}` but whose `strategy.matrix` has no
    `node_version` key at all, when candidates are resolved, then an
    `AssertionError` must be raised rather than silently returning an empty
    list or the raw expression string."""
    job = {
        "strategy": {"matrix": {"other_key": ["1"]}},
        "steps": [
            {
                "uses": "actions/setup-node@v5",
                "with": {"node-version": "${{ matrix.node_version }}"},
            }
        ],
    }
    step = job["steps"][0]
    with pytest.raises(AssertionError):
        _node_version_candidates(job, step)


# --- Synthetic self-tests: _lowest_lower_bound ------------------------------


def test_lowest_lower_bound_returns_the_smallest_lower_bound_across_a_gapped_union() -> None:
    """Given the three half-open intervals a gapped, multi-alternative
    `engines.node` union (`^18.18.0 || ^19.8.0 || >=20.0.0`) parses to, when
    the lowest lower bound is computed, then it must be `18.18.0` -- the
    first alternative's lower bound, even though it is not the first
    interval encountered in parse order for every possible input."""
    intervals = parse_node_engines_range("^18.18.0 || ^19.8.0 || >= 20.0.0")
    assert _lowest_lower_bound(intervals) == (18, 18, 0)


def test_lowest_lower_bound_is_order_independent() -> None:
    """Given the same three intervals in a deliberately shuffled order, when
    the lowest lower bound is computed, then the result must be unchanged --
    proving this does not depend on the domain already being sorted."""
    intervals = parse_node_engines_range(">= 20.0.0 || ^18.18.0 || ^19.8.0")
    assert _lowest_lower_bound(intervals) == (18, 18, 0)


# --- AC5: every setup-node step in the whole workflow is within span -------


def test_every_setup_node_step_in_the_workflow_requests_a_version_within_engines_node_span() -> (
    None
):
    """Given `.github/workflows/test.yml`, when every `actions/setup-node`
    step across every job (not only `frontend`) is read -- resolving any
    `${{ matrix.<key> }}` expression against that job's own
    `strategy.matrix` first -- then every concrete Node version it can
    resolve to must fall inside `frontend/package.json`'s declared
    `engines.node` span. Supersedes and replaces AC3's now-removed
    `test_ci_frontend_job_node_version_is_within_engines_node_span` (see the
    module docstring's "GH-17: generalizing the single-version CI check
    above ... and removing AC3's real-world test" section for exactly why
    the old test could not be left in place once `node-version` becomes a
    `${{ matrix.<key> }}` expression), since GH-17 also adds a second job
    (`frontend-lint`) that needs Node -- issue #17, AC5.

    Does not cover: which *specific* versions the `frontend` job's matrix
    must contain (AC7-AC9's concern below), only that whichever versions
    any job's `actions/setup-node` step can resolve to are individually
    valid per `engines.node`."""
    workflow_data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    setup_node_steps = _all_setup_node_steps(workflow_data)
    assert setup_node_steps, (
        f"expected at least one 'actions/setup-node' step somewhere in "
        f"{WORKFLOW_PATH.relative_to(REPO_ROOT)}; found none."
    )

    package_json = _read_frontend_package_json()
    own_spec = package_json.get("engines", {}).get("node")
    assert own_spec, (
        f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)} has no 'engines.node', so no "
        "setup-node step's node-version can be checked against it."
    )
    own_intervals = parse_node_engines_range(own_spec)

    violations: list[str] = []
    for job_name, job, step in setup_node_steps:
        try:
            candidates = _node_version_candidates(job, step)
        except AssertionError as exc:
            violations.append(f"job {job_name!r}: {exc}")
            continue
        for candidate in candidates:
            if not candidate:
                violations.append(f"job {job_name!r}: step sets no 'with.node-version'")
                continue
            try:
                interval = _parse_version_token(candidate)
            except ValueError as exc:
                violations.append(f"job {job_name!r}: unparsable node-version {candidate!r}: {exc}")
                continue
            if not _is_subset_of_union(interval, own_intervals):
                violations.append(
                    f"job {job_name!r}: node-version {candidate!r} falls outside "
                    f"engines.node span {own_spec!r}"
                )

    assert not violations, (
        f"{WORKFLOW_PATH.relative_to(REPO_ROOT)} has 'actions/setup-node' step(s) requesting "
        f"Node version(s) outside the engines.node span declared in "
        f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)} ({own_spec!r}):\n" + "\n".join(violations)
    )


# --- AC7: the frontend job's setup-node step references its own matrix key -


def test_frontend_job_setup_node_step_references_its_own_matrix_key() -> None:
    """Given `.github/workflows/test.yml`, when the `frontend` job's
    `strategy.matrix` is read, then it must have exactly one key mapped to a
    non-empty list, and the job's `actions/setup-node` step's
    `with.node-version` must be exactly the expression `${{ matrix.<key> }}`
    referencing that same key -- issue #17, AC7."""
    workflow_data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    matrix = _frontend_job_matrix(workflow_data)
    key, _versions = _matrix_key_and_versions(matrix)

    setup_node_step = _frontend_setup_node_step(workflow_data)
    node_version = str(setup_node_step.get("with", {}).get("node-version", "")).strip()
    expected = f"${{{{ matrix.{key} }}}}"

    assert node_version == expected, (
        f"expected the 'frontend' job's 'actions/setup-node' step to set "
        f"with.node-version to {expected!r} (referencing strategy.matrix.{key}), found "
        f"{node_version!r}."
    )


# --- AC8: every frontend matrix entry is within the engines.node span ------


def test_every_frontend_matrix_entry_is_within_the_engines_node_span() -> None:
    """Given `.github/workflows/test.yml`'s `frontend` job's
    `strategy.matrix` entries, when each is parsed as a bare version token,
    then it must fall entirely within `frontend/package.json`'s declared
    `engines.node` span -- issue #17, AC8.

    This is the trap the task's own briefing calls out by name: a floor leg
    spelled `"20"` parses to the interval `[20.0.0, 21.0.0)`, which is *not*
    a subset of `^20.9.0 || >=21.1.0` (it dips below `20.9.0`), so this test
    fails loudly if the floor leg is under-specified to a bare major
    instead of the full `20.9.0`."""
    workflow_data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    matrix = _frontend_job_matrix(workflow_data)
    _key, versions = _matrix_key_and_versions(matrix)

    package_json = _read_frontend_package_json()
    own_spec = package_json.get("engines", {}).get("node")
    assert own_spec, (
        f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)} has no 'engines.node', so matrix "
        "entries cannot be checked against it."
    )
    own_intervals = parse_node_engines_range(own_spec)

    violations = []
    for version in versions:
        try:
            interval = _parse_version_token(version)
        except ValueError as exc:
            violations.append(f"{version!r}: {exc}")
            continue
        if not _is_subset_of_union(interval, own_intervals):
            violations.append(f"{version!r} falls outside engines.node span {own_spec!r}")

    assert not violations, (
        f"expected every entry of {WORKFLOW_PATH.relative_to(REPO_ROOT)}'s 'frontend' job "
        f"strategy.matrix to fall inside engines.node={own_spec!r}; violations:\n"
        + "\n".join(violations)
    )


# --- AC9: the matrix entry set is exactly the floor leg and the nvmrc leg --


def test_frontend_matrix_entry_set_is_exactly_the_floor_and_the_nvmrc_entry() -> None:
    """Given `.github/workflows/test.yml`'s `frontend` job's
    `strategy.matrix` entries, `frontend/package.json`'s declared
    `engines.node` span, and the repository's own `.nvmrc`, when the matrix
    entry set is compared against (a) the entry whose parsed lower bound
    equals `engines.node`'s lowest lower bound across its whole `||`-union,
    and (b) the entry that covers `.nvmrc`'s declared version, then the
    matrix entry set must be exactly those two -- no extra legs, no
    substitutes -- so CI exercises the oldest Node version this frontend
    still claims to support alongside the exact version every contributor's
    `nvm use`/CI's own `.nvmrc`-driven tooling resolves to -- issue #17,
    AC9.

    Neither expected version is hard-coded in this test: both are derived
    at test time from `frontend/package.json`'s `engines.node` and the
    repository's own `.nvmrc` file, per AC9's own requirement. This test
    does not need editing if either source changes -- only if the
    *relationship* the matrix is supposed to have with them breaks."""
    workflow_data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    matrix = _frontend_job_matrix(workflow_data)
    _key, versions = _matrix_key_and_versions(matrix)

    package_json = _read_frontend_package_json()
    own_spec = package_json.get("engines", {}).get("node")
    assert own_spec, (
        f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)} has no 'engines.node'; cannot derive "
        "the expected floor version."
    )
    own_intervals = parse_node_engines_range(own_spec)
    floor = _lowest_lower_bound(own_intervals)

    nvmrc_candidates = [path for path in NVMRC_CANDIDATES if path.is_file()]
    assert nvmrc_candidates, (
        "expected a '.nvmrc' at one of "
        f"{[str(p.relative_to(REPO_ROOT)) for p in NVMRC_CANDIDATES]}; found none."
    )
    nvmrc_token = _first_nvmrc_version_token(nvmrc_candidates[0])
    nvmrc_interval = _parse_version_token(nvmrc_token)

    parsed_by_version: dict[str, Interval] = {}
    for version in versions:
        try:
            parsed_by_version[version] = _parse_version_token(version)
        except ValueError as exc:
            pytest.fail(f"matrix entry {version!r} could not be parsed as a version token: {exc}")

    floor_entries = {v for v, interval in parsed_by_version.items() if interval[0] == floor}
    nvmrc_entries = {
        v
        for v, interval in parsed_by_version.items()
        if _is_subset_of_union(nvmrc_interval, [interval])
    }

    assert floor_entries, (
        f"expected one matrix entry whose parsed lower bound equals engines.node's lowest "
        f"lower bound {floor!r} (derived from engines.node={own_spec!r}); matrix entries: "
        f"{sorted(versions)}"
    )
    assert nvmrc_entries, (
        f"expected one matrix entry that covers .nvmrc's declared version {nvmrc_token!r}; "
        f"matrix entries: {sorted(versions)}"
    )

    expected_entries = floor_entries | nvmrc_entries
    assert set(versions) == expected_entries, (
        f"expected {WORKFLOW_PATH.relative_to(REPO_ROOT)}'s 'frontend' job strategy.matrix "
        f"entries to be exactly {sorted(expected_entries)} (the floor leg matching "
        f"engines.node's lowest lower bound {floor!r} and the leg covering .nvmrc's "
        f"{nvmrc_token!r}), found {sorted(versions)}."
    )


# --- AC10: strategy.fail-fast is disabled -----------------------------------


def test_frontend_job_strategy_has_fail_fast_disabled() -> None:
    """Given `.github/workflows/test.yml`, when the `frontend` job's
    `strategy.fail-fast` is read, then it must be the boolean `False` -- so
    one matrix leg's flaky Vitest failure (issue #70) cannot cancel the
    other leg's run before it has a chance to report -- issue #17, AC10."""
    workflow_data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    frontend_job = workflow_data.get("jobs", {}).get("frontend")
    assert frontend_job is not None, (
        f"expected a 'frontend' job in {WORKFLOW_PATH.relative_to(REPO_ROOT)}"
    )
    strategy = frontend_job.get("strategy", {})
    assert "fail-fast" in strategy, (
        f"expected the 'frontend' job's strategy to set 'fail-fast'; found strategy={strategy!r}"
    )
    assert strategy["fail-fast"] is False, (
        "expected the 'frontend' job's strategy.fail-fast to be the boolean False, found "
        f"{strategy['fail-fast']!r}"
    )


# =============================================================================
# GH-49 / issue #49, AC6: `vite`, a *transitive* dependency (pulled in only by
# `vitest`, never declared directly in `frontend/package.json`'s own
# `dependencies` or `devDependencies`), is the package whose own
# `engines.node` actually gates what CI's `frontend` job can run once
# `vitest` is bumped to a major version that itself depends on a `vite`
# major requiring Node `^20.19.0 || >=22.12.0` (measured against
# `vite@8.2.2`'s own `engines` field at authoring time, via `npm view
# vite@8.2.2 engines`).
#
# `_CONSTRAINED_DEPENDENCY_ENGINES` above is built only from
# `_direct_dependency_names(_FRONTEND_PACKAGE_JSON_DATA)` (see that
# dict's own definition), so
# `test_frontend_engines_node_is_compatible_with_dependency`'s
# parametrization never includes `vite` and never will, no matter how
# narrow or wide `engines.node` becomes: that parametrized guard checks
# *declared*, direct dependencies only, by design (see AC1's own section
# above). `vite` needs its own, separate guard because it is the one
# package in this dependency graph that is both (a) actually installed by
# `npm ci` and executed by `npm test` in CI (as `vitest`'s own
# bundler/dev-server dependency) and (b) invisible to every existing
# `engines.node` check in this module, since none of them ever look past
# `package.json`'s direct dependency names. That gap between "runs in CI"
# and "declared anywhere checked" is the same shape of gap GH-16 and GH-17
# each closed for a different artifact (a hard-coded CI node-version with
# nothing tying it to `engines.node`; a single-leg CI matrix with nothing
# tying it to a transitively-required bundler's own floor) -- this closes
# it for a transitive dependency specifically.
#
# Reuses `_dependency_engines_node`, `parse_node_engines_range`, and
# `_is_subset_of_union` unchanged: `_dependency_engines_node` already reads
# any `packages['node_modules/<name>']` entry from `package-lock.json`
# (including `vite`'s, which is present in the real lockfile regardless of
# `vite` never being a *direct* dependency), so this AC needs no new
# parsing machinery, only a new call site naming `vite` explicitly.
# =============================================================================


def test_frontend_engines_node_is_compatible_with_transitive_vite_dependency() -> None:
    """Given `frontend/package.json`'s declared `engines.node` and `vite`'s
    own `engines.node` (read from `package-lock.json`'s
    `packages['node_modules/vite']`, even though `vite` is never a *direct*
    dependency), when the declared range is compared against `vite`'s, then
    the declared range must not claim support for any Node version `vite`'s
    own `engines.node` excludes -- issue #49, AC6.

    `vite` is checked here, separately from
    `test_frontend_engines_node_is_compatible_with_dependency` above,
    because it is a transitive dependency (pulled in only via `vitest`,
    never listed in `frontend/package.json`'s own
    `dependencies`/`devDependencies`), so `_CONSTRAINED_DEPENDENCY_ENGINES`'s
    parametrization -- built only from `_direct_dependency_names` -- never
    includes it (see the "GH-49 / issue #49, AC6" section above this test).
    `npm ci` still installs, and `npm test` still runs, `vite` (as `vitest`'s
    own bundler/dev-server dependency) regardless of it never being declared
    directly, so a mismatch here is exactly as real a CI failure risk as a
    mismatch against a direct dependency would be.

    Does not cover: any other transitive dependency besides `vite` -- this
    is a targeted guard for the one transitive package issue #49's own
    investigation identified as `engines.node`-constraining, not a general
    "check every transitive dependency" guard."""
    package_json = _read_frontend_package_json()
    package_lock = _read_frontend_package_lock()
    own_spec = package_json.get("engines", {}).get("node")
    assert own_spec, (
        f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)} has no 'engines.node', so it cannot "
        "be checked for compatibility with vite's own engines.node."
    )
    vite_spec = _dependency_engines_node(package_lock, "vite")
    assert vite_spec, (
        f"{FRONTEND_PACKAGE_LOCK.relative_to(REPO_ROOT)} has no "
        "packages['node_modules/vite'].engines.node; expected vite to declare one "
        "(present for both vite@5.4.21 and vite@8.2.2, measured at authoring time)."
    )

    try:
        own_intervals = parse_node_engines_range(own_spec)
        vite_intervals = parse_node_engines_range(vite_spec)
    except ValueError as exc:
        pytest.fail(f"could not parse an engines.node range while checking vite: {exc}")

    uncovered = [
        interval for interval in own_intervals if not _is_subset_of_union(interval, vite_intervals)
    ]
    assert not uncovered, (
        f"{FRONTEND_PACKAGE_JSON.relative_to(REPO_ROOT)} declares engines.node={own_spec!r}, "
        f"which claims support for Node versions vite's own engines.node ({vite_spec!r}) "
        "excludes. vite is a transitive dependency (via vitest), never listed in "
        "package.json's own dependencies/devDependencies, which is why this check exists "
        "separately from the parametrized direct-dependency guard above."
    )


# --- Synthetic self-test: the transitive-vite guard's own reasoning --------


def test_synthetic_transitive_dependency_engines_pipeline_detects_an_incompatible_declaration() -> (
    None
):
    """Given a synthetic package-lock.json entry shaped like `vite`'s (a
    package present under `packages['node_modules/vite']` but absent from
    `package.json`'s own `dependencies`/`devDependencies`, so it would never
    appear in `_CONSTRAINED_DEPENDENCY_ENGINES`), when a declared
    `engines.node` that claims support for a Node version this synthetic
    transitive dependency's own `engines.node` excludes is checked against
    it directly (the same `_dependency_engines_node` +
    `parse_node_engines_range` + `_is_subset_of_union` steps
    `test_frontend_engines_node_is_compatible_with_transitive_vite_dependency`
    performs), then the incompatibility must be reported -- proving this
    combination of helpers detects a transitive-dependency mismatch on
    synthetic input, independent of whatever this repository's real `vite`
    entry currently says."""
    package_json = {"dependencies": {}, "devDependencies": {"some-tool": "^1.0.0"}}
    package_lock = {
        "packages": {
            "node_modules/vite": {"engines": {"node": "^20.19.0 || >=22.12.0"}},
        }
    }
    # Confirm the synthetic setup actually matches the real shape this test
    # exists to guard: `vite` absent from direct dependency names, but
    # present (with its own engines.node) in the lockfile.
    assert "vite" not in _direct_dependency_names(package_json)
    vite_spec = _dependency_engines_node(package_lock, "vite")
    assert vite_spec is not None

    own_spec = ">=20.9.0"  # claims support for 20.9.0-20.18.x, which vite excludes
    own_intervals = parse_node_engines_range(own_spec)
    vite_intervals = parse_node_engines_range(vite_spec)
    uncovered = [
        interval for interval in own_intervals if not _is_subset_of_union(interval, vite_intervals)
    ]
    assert uncovered != []
