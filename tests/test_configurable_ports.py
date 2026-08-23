"""Tests for GH-46: every port this repository binds is hardcoded, which
makes both the container stack and `make backend-dev` unstartable on a
developer machine where those exact ports are unavailable.

Measured at authoring time, this is what is hardcoded::

    docker-compose.yml:5        - "80:80"
    docker-compose.yml:6        - "443:443"
    docker-compose.dev-db.yml:7 - "5432:5432"
    Makefile:23                 $(UV) run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend
    Makefile:29                 cd frontend && npm run dev
    .env.example                 no port variables at all

Two concrete failure modes motivate this, both observed directly rather than
hypothesized:

* Rootless podman cannot bind ports below 1024 regardless of whether they
  are free (`net.ipv4.ip_unprivileged_port_start` gates this), so
  `docker-compose.yml`'s `"80:80"`/`"443:443"` publications on `caddy` --
  the only service in that file that publishes anything to the host, since
  `backend`, `frontend`, `collector` and `postgres` only talk to each other
  over the compose network -- block the whole stack for a rootless user even
  when 80 and 443 are otherwise unoccupied.
* `Makefile:23`'s hardcoded `--port 8000` collides with whatever else is
  already listening on 8000 on the developer's machine, which blocks
  `make backend-dev` outright; this is not hypothetical; it is the
  reported, reproduced state of the reporting machine.

`docker-compose.yml` already carries the `${VAR:-default}` substitution
pattern for everything except ports, e.g.
`CADDY_DOMAIN: ${CADDY_DOMAIN:-localhost}` (`docker-compose.yml:8`) and
`LOG_LEVEL: ${LOG_LEVEL:-INFO}` (`docker-compose.yml:46`). GH-46's accepted
fix extends that same pattern to the five port values below, and this suite
pins those five variable names as
the contract the fix must satisfy, since `.env.example` must document them
by name (AC4) and a name has to be decided somewhere for that to be
testable:

* `HTTP_PORT`      -- `docker-compose.yml`'s `caddy` "80:80" publication (AC1)
* `HTTPS_PORT`     -- `docker-compose.yml`'s `caddy` "443:443" publication (AC1)
* `POSTGRES_PORT`  -- `docker-compose.dev-db.yml`'s postgres "5432:5432" publication (AC2)
* `BACKEND_PORT`   -- `Makefile`'s `backend-dev` `--port 8000` (AC3)
* `FRONTEND_PORT`  -- `Makefile`'s `frontend-dev` (`next dev`'s own port) (AC3)

For every one of these, the required behavior is the same shape: overriding
the environment variable must change the effective port, and leaving it
unset must reproduce today's exact default -- nothing about default
behavior may change for a developer who has these ports free.

-- How each side is exercised without starting anything --

`docker-compose.yml` and `docker-compose.dev-db.yml` are rendered with
`docker compose -f <file> config`, which resolves every `${VAR:-default}`
substitution and prints the fully-materialized compose document without
creating, starting, or even pulling images for a single container (verified
directly against this repository's compose files during authoring; see
`_run_compose_config`). The `docker` binary in this environment is podman's
Docker-CLI emulation layer, which writes an informational banner to stderr
("Executing external compose provider ...") on every invocation; that
banner is irrelevant noise here and is discarded, but exit code 0 and valid
YAML on stdout were both confirmed empirically before relying on this
technique.

`Makefile`'s `backend-dev` and `frontend-dev` are exercised with
`make -n`, which prints the fully variable-substituted recipe line(s) a
real invocation would run, without ever invoking a shell to execute them --
so this never starts uvicorn or `next dev`, both of which are long-running
and one of which (uvicorn, per `--port 8000`) would collide with whatever
already occupies 8000 on the machine running this suite.

`frontend-dev`'s only recipe line, `cd frontend && npm run dev` (`Makefile:29`),
does not itself mention a port at all -- `next dev` picks its own port.
`frontend/node_modules/next/dist/bin/next` (the actual installed CLI in this
repository, inspected directly, not assumed) defines
`-p, --port` via commander as
`.argParser(parseValidPositiveInteger).default(3000).env('PORT')`, and
running the installed CLI's own `next dev --help` (which prints and exits;
it does not bind a port) confirms this in its rendered help text:
`-p, --port <port>  ... (default: 3000, env: PORT)`. So a GH-46 fix for
`frontend-dev` has two accepted shapes: leave the recipe as-is (relying on
`next dev`'s own built-in default of 3000, still satisfying "default is
3000 when FRONTEND_PORT is unset") and export `PORT=$(FRONTEND_PORT)`
(or pass `--port $(FRONTEND_PORT)`) so the override reaches `next dev`.
`test_next_dev_cli_still_defaults_to_port_3000_and_reads_port_env_var`
below pins that upstream contract directly against the installed CLI, so
that if a future Next.js upgrade changes it, this suite fails loudly at the
boundary instead of `frontend-dev`'s override silently stopping working.

-- What is deliberately NOT tested here, and why --

Validating malformed port values (e.g. `HTTP_PORT=not-a-number`) is out of
scope: GH-46 is a default-override feature for a value only the developer
running the tooling ever sets (never attacker-controlled input reaching
this repository over a network boundary), scope for this round is frozen,
and input-range validation was not requested as part of GH-46's acceptance
criteria. This is a plain out-of-scope exclusion, not a description of a
known bug in intended-complete functionality.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import NamedTuple

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKER_COMPOSE_PATH = REPO_ROOT / "docker-compose.yml"
DOCKER_COMPOSE_DEV_DB_PATH = REPO_ROOT / "docker-compose.dev-db.yml"
MAKEFILE_PATH = REPO_ROOT / "Makefile"
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"
ENV_EXAMPLE_TEXT = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")

_DOCKER_BINARY = shutil.which("docker")
_MAKE_BINARY = shutil.which("make")
_NODE_BINARY = shutil.which("node")

# The five port-override variable names GH-46's fix must introduce -- see
# the module docstring for why these particular names are pinned rather
# than left to the implementation's discretion.
COMPOSE_PORT_ENV_VARS = ("HTTP_PORT", "HTTPS_PORT", "POSTGRES_PORT")
MAKE_PORT_ENV_VARS = ("BACKEND_PORT", "FRONTEND_PORT")
ALL_PORT_ENV_VARS = COMPOSE_PORT_ENV_VARS + MAKE_PORT_ENV_VARS


def _run_compose_config(
    compose_path: Path, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run `docker compose -f compose_path config` and return the completed
    process untouched (no assertions here, matching this repository's
    existing convention of asserting inside the test body -- see
    `tests/test_makefile_pythonpath.py`'s `_run_probe_target`).

    `config` resolves every `${VAR:-default}` substitution and renders the
    full compose document to stdout without creating or starting a single
    container. Every one of GH-46's port-override variables is scrubbed
    from the base environment before applying `extra_env`, so a variable
    left over in the calling shell can never leak into a "default" case and
    make it look like an override took effect when it did not.
    """
    env = dict(os.environ)
    for override_var in COMPOSE_PORT_ENV_VARS:
        env.pop(override_var, None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [_DOCKER_BINARY, "compose", "-f", str(compose_path), "config"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _published_port(config: dict, service: str, target_port: int) -> str | None:
    """Return the host-side `published` value `docker compose config`
    resolved for `service`'s port mapping whose container-side `target` is
    `target_port`, as a string (compose renders it quoted), or `None` if no
    such service or mapping exists in `config`."""
    service_config = config.get("services", {}).get(service, {})
    for mapping in service_config.get("ports", []):
        if mapping.get("target") == target_port:
            published = mapping.get("published")
            return None if published is None else str(published)
    return None


class _PortMappingCase(NamedTuple):
    compose_path: Path
    service: str
    target_port: int
    env_var: str
    default_published: str
    override_value: str


# One case per host-published port GH-46 covers. `docker-compose.yml`'s
# `frontend`, `backend`, `collector` and `postgres` services publish
# nothing to the host at all (only `caddy` does; they reach each other over
# the compose network via `reverse_proxy backend:8000` in the Caddyfile),
# so `caddy`'s two mappings plus `docker-compose.dev-db.yml`'s postgres
# mapping are the complete set of AC1/AC2 cases.
_PORT_MAPPING_CASES: list[_PortMappingCase] = [
    _PortMappingCase(DOCKER_COMPOSE_PATH, "caddy", 80, "HTTP_PORT", "80", "8080"),
    _PortMappingCase(DOCKER_COMPOSE_PATH, "caddy", 443, "HTTPS_PORT", "443", "8443"),
    _PortMappingCase(
        DOCKER_COMPOSE_DEV_DB_PATH, "postgres", 5432, "POSTGRES_PORT", "5432", "15432"
    ),
]
_PORT_MAPPING_IDS = [f"{case.service}-{case.target_port}" for case in _PORT_MAPPING_CASES]


def _skip_without_docker() -> None:
    if _DOCKER_BINARY is None:
        pytest.skip("docker (or podman's docker-CLI emulation) is not on PATH.")


@pytest.mark.parametrize("case", _PORT_MAPPING_CASES, ids=_PORT_MAPPING_IDS)
def test_compose_port_publish_defaults_to_todays_hardcoded_value_when_env_var_unset(
    case: _PortMappingCase,
) -> None:
    """Given `case.compose_path`, when it is rendered via `docker compose
    config` with `case.env_var` unset, then the host-side `published` port
    for `case.service`'s `case.target_port` mapping must equal
    `case.default_published` -- today's hardcoded value -- so introducing
    the override does not change behavior for a developer who never sets
    the variable (AC1/AC2, "nuvarande värden som default")."""
    _skip_without_docker()
    result = _run_compose_config(case.compose_path)
    assert result.returncode == 0, (
        f"`docker compose -f {case.compose_path} config` exited {result.returncode}.\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    config = yaml.safe_load(result.stdout)
    published = _published_port(config, case.service, case.target_port)
    assert published == case.default_published, (
        f"with {case.env_var} unset, {case.compose_path}'s `{case.service}` service published "
        f"port {published!r} for container port {case.target_port}, expected "
        f"{case.default_published!r} (today's hardcoded default) to be unchanged.\n"
        f"--- rendered config ---\n{result.stdout}"
    )


@pytest.mark.parametrize("case", _PORT_MAPPING_CASES, ids=_PORT_MAPPING_IDS)
def test_compose_port_publish_is_overridable_via_its_env_var(case: _PortMappingCase) -> None:
    """Given `case.compose_path`, when it is rendered via `docker compose
    config` with `case.env_var` set to `case.override_value`, then the
    host-side `published` port for `case.service`'s `case.target_port`
    mapping must equal `case.override_value`, while the container-side
    `target` must remain `case.target_port` unchanged -- proving the
    override reaches only the host publication, not the in-network port
    other services (or the Caddyfile's `reverse_proxy`) rely on (AC1/AC2)."""
    _skip_without_docker()
    result = _run_compose_config(case.compose_path, {case.env_var: case.override_value})
    assert result.returncode == 0, (
        f"`docker compose -f {case.compose_path} config` (with {case.env_var}="
        f"{case.override_value}) exited {result.returncode}.\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    config = yaml.safe_load(result.stdout)
    published = _published_port(config, case.service, case.target_port)
    assert published == case.override_value, (
        f"setting {case.env_var}={case.override_value} in the environment had no effect on "
        f"{case.compose_path}'s `{case.service}` service: published port is still {published!r} "
        f"instead of {case.override_value!r}. The port publication is not yet parameterized "
        f"with `${{{case.env_var}:-{case.default_published}}}` (GH-46).\n"
        f"--- rendered config ---\n{result.stdout}"
    )


@pytest.mark.parametrize("case", _PORT_MAPPING_CASES, ids=_PORT_MAPPING_IDS)
def test_compose_port_publish_falls_back_to_default_when_env_var_is_set_but_empty(
    case: _PortMappingCase,
) -> None:
    """Given `case.compose_path`, when it is rendered via `docker compose
    config` with `case.env_var` present in the environment but set to the
    empty string, then the host-side `published` port must still fall back
    to `case.default_published`. This is an edge case of AC1/AC2's default
    requirement: the compose specification's `${VAR:-default}` operator
    (the `-` variant, already used throughout this file for e.g.
    `CADDY_DOMAIN: ${CADDY_DOMAIN:-localhost}`, `docker-compose.yml:8`)
    treats an empty value the same as an unset one -- confirmed directly
    against this compose engine during authoring by setting
    `CADDY_DOMAIN=""` and observing `CADDY_DOMAIN: localhost` in the
    rendered output, rather than `CADDY_DOMAIN: ""`. An env-tooling
    footgun (an empty-but-exported `HTTP_PORT=` left over in a shell
    profile, say) must not silently render an invalid empty port
    publication."""
    _skip_without_docker()
    result = _run_compose_config(case.compose_path, {case.env_var: ""})
    assert result.returncode == 0, (
        f"`docker compose -f {case.compose_path} config` (with {case.env_var}='') exited "
        f"{result.returncode}.\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    config = yaml.safe_load(result.stdout)
    published = _published_port(config, case.service, case.target_port)
    assert published == case.default_published, (
        f"with {case.env_var} set to the empty string, {case.compose_path}'s `{case.service}` "
        f"service published port {published!r} for container port {case.target_port}, expected "
        f"it to fall back to {case.default_published!r} the same way "
        f"`${{{case.env_var}:-{case.default_published}}}` (the `:-` colon variant, matching this "
        f"file's existing `${{CADDY_DOMAIN:-localhost}}` pattern) does -- not the `-` variant, "
        "which would only fall back for a wholly unset variable, not an empty one.\n"
        f"--- rendered config ---\n{result.stdout}"
    )


# --- Makefile: backend-dev / frontend-dev (AC3) ---


def _make_dry_run(
    target: str, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run `make -n <target>`, which prints the fully variable-substituted
    recipe line(s) a real `make <target>` would execute, without invoking a
    shell to run any of them -- so this never starts uvicorn or `next dev`.
    Both `BACKEND_PORT` and `FRONTEND_PORT` are scrubbed from the base
    environment before applying `extra_env`, for the same leftover-shell-
    variable reason as `_run_compose_config`."""
    env = dict(os.environ)
    for override_var in MAKE_PORT_ENV_VARS:
        env.pop(override_var, None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["make", "--no-print-directory", "-n", "-C", str(REPO_ROOT), target],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _skip_without_make() -> None:
    if _MAKE_BINARY is None:
        pytest.skip("make is not on PATH; cannot exercise the Makefile's recipes.")


_BACKEND_PORT_RE = re.compile(r"--port[ =](\d+)")
# Any bare 4-5 digit token in frontend-dev's dry-run output, used to detect
# whether the recipe references a port explicitly at all (see
# `test_frontend_dev_recipe_defaults_to_port_3000_or_makes_no_explicit_port_reference`).
_PORT_LIKE_TOKEN_RE = re.compile(r"\b(\d{4,5})\b")


def test_backend_dev_recipe_uses_port_8000_by_default() -> None:
    """Given `Makefile`'s `backend-dev` target (`Makefile:22-23`), when it
    is rendered via `make -n backend-dev` with `BACKEND_PORT` unset, then
    the printed recipe must still bind uvicorn to `--port 8000` -- today's
    hardcoded default -- unchanged (AC3, default preserved)."""
    _skip_without_make()
    result = _make_dry_run("backend-dev")
    assert result.returncode == 0, (
        f"`make -n backend-dev` exited {result.returncode}.\n--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
    match = _BACKEND_PORT_RE.search(result.stdout)
    assert match, (
        f"`make -n backend-dev`'s dry-run output does not contain a `--port <n>` token at all: "
        f"{result.stdout!r}"
    )
    assert match.group(1) == "8000", (
        f"with BACKEND_PORT unset, `make -n backend-dev` printed `--port {match.group(1)}`, "
        f"expected `--port 8000` (today's hardcoded default) to be unchanged.\n"
        f"--- stdout ---\n{result.stdout}"
    )


def test_backend_dev_recipe_port_is_overridable_via_backend_port_env_var() -> None:
    """Given `Makefile`'s `backend-dev` target, when it is rendered via
    `make -n backend-dev` with `BACKEND_PORT=9001` in the environment, then
    the printed recipe must bind uvicorn to `--port 9001` instead of the
    hardcoded 8000 -- proving the override reaches the command that would
    actually run (AC3)."""
    _skip_without_make()
    result = _make_dry_run("backend-dev", {"BACKEND_PORT": "9001"})
    assert result.returncode == 0, (
        f"`make -n backend-dev` (with BACKEND_PORT=9001) exited {result.returncode}.\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    match = _BACKEND_PORT_RE.search(result.stdout)
    assert match and match.group(1) == "9001", (
        "setting BACKEND_PORT=9001 in the environment had no effect on `backend-dev`'s dry-run "
        f"recipe: {result.stdout!r}. `backend-dev`'s recipe (`Makefile:22-23`) does not yet "
        "read BACKEND_PORT (GH-46)."
    )


def test_frontend_dev_recipe_defaults_to_port_3000_or_makes_no_explicit_port_reference() -> None:
    """Given `Makefile`'s `frontend-dev` target (`Makefile:28-29`,
    `cd frontend && npm run dev`), when it is rendered via `make -n
    frontend-dev` with `FRONTEND_PORT` unset, then any port-like numeric
    token the recipe prints must be 3000, or the recipe must print no
    port-like token at all -- both are accepted, since `next dev`'s own
    CLI already defaults its `--port` option to 3000 when neither `--port`
    nor `PORT` is supplied (confirmed directly against the installed CLI;
    see `test_next_dev_cli_still_defaults_to_port_3000_and_reads_port_env_var`),
    so a fix that leaves `frontend-dev` untouched when unset is exactly as
    correct as one that spells 3000 out explicitly (AC3, default
    preserved)."""
    _skip_without_make()
    result = _make_dry_run("frontend-dev")
    assert result.returncode == 0, (
        f"`make -n frontend-dev` exited {result.returncode}.\n--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
    found_ports = set(_PORT_LIKE_TOKEN_RE.findall(result.stdout))
    assert found_ports <= {"3000"}, (
        f"with FRONTEND_PORT unset, `make -n frontend-dev` printed port-like token(s) "
        f"{sorted(found_ports)!r} other than 3000: {result.stdout!r}. The default effective "
        "port must remain 3000 when the override is unset."
    )


def test_frontend_dev_recipe_port_is_overridable_via_frontend_port_env_var() -> None:
    """Given `Makefile`'s `frontend-dev` target, when it is rendered via
    `make -n frontend-dev` with `FRONTEND_PORT=4000` in the environment,
    then the printed recipe must reference 4000 (as `PORT=4000`, `--port
    4000`, or an equivalent -- the exact mechanism is not prescribed, only
    that the override visibly reaches the command that would run), proving
    the override is not silently dropped (AC3)."""
    _skip_without_make()
    result = _make_dry_run("frontend-dev", {"FRONTEND_PORT": "4000"})
    assert result.returncode == 0, (
        f"`make -n frontend-dev` (with FRONTEND_PORT=4000) exited {result.returncode}.\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    assert "4000" in result.stdout, (
        "setting FRONTEND_PORT=4000 in the environment had no effect on `frontend-dev`'s "
        f"dry-run recipe: {result.stdout!r}. `frontend-dev`'s recipe (`Makefile:28-29`, "
        "`cd frontend && npm run dev`) does not yet forward FRONTEND_PORT into the invoked "
        "`npm run dev` / `next dev` command (GH-46)."
    )


# --- Contract test: the upstream CLI boundary frontend-dev's fix relies on ---


def test_next_dev_cli_still_defaults_to_port_3000_and_reads_port_env_var() -> None:
    """Given `frontend/node_modules/next`, the `next` package this
    repository's `frontend-dev` actually invokes (via `npm run dev` ->
    `next dev`), when its CLI is asked for `--help` (which prints and
    exits; it does not bind a port or start a server), then its `-p,
    --port` option's rendered help text must still advertise a default of
    3000 sourced from the `PORT` environment variable. This pins the
    external API boundary GH-46's `frontend-dev` fix depends on for AC3's
    "3000 as default, overridable" requirement: whichever accepted shape
    the fix takes (leaving `frontend-dev` untouched and trusting `next
    dev`'s own default, or explicitly exporting `PORT=$(FRONTEND_PORT)`),
    it depends on `next dev` resolving its port from `PORT`/a 3000 default
    exactly as it does today. If a future Next.js upgrade changes this
    contract, this test fails at the boundary instead of `frontend-dev`'s
    override silently stopping working."""
    if _NODE_BINARY is None:
        pytest.skip("node is not on PATH; cannot exercise the installed next CLI's --help.")
    next_bin = REPO_ROOT / "frontend" / "node_modules" / ".bin" / "next"
    if not next_bin.exists():
        pytest.skip(
            "frontend/node_modules/.bin/next does not exist; run `npm ci` in frontend/ first."
        )
    result = subprocess.run(
        [_NODE_BINARY, str(next_bin), "dev", "--help"],
        cwd=REPO_ROOT / "frontend",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, (
        f"`next dev --help` exited {result.returncode} instead of printing help and exiting.\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    assert re.search(r"-p,\s*--port.*default:\s*3000.*env:\s*PORT", result.stdout), (
        "the installed `next` CLI's `next dev --help` no longer advertises `-p, --port` as "
        f"defaulting to 3000 via the `PORT` environment variable:\n{result.stdout}\nThis is the "
        "contract `frontend-dev`'s GH-46 fix depends on; if it changed, that fix needs revisiting."
    )


# --- .env.example (AC4) ---


@pytest.mark.parametrize("env_var", ALL_PORT_ENV_VARS)
def test_env_example_documents_port_override_variable(env_var: str) -> None:
    """Given `.env.example`, when its contents are inspected, then it must
    mention `env_var` by name -- as a live assignment or a commented-out
    example, either satisfies "documented" -- so a developer discovers the
    override exists without having to read `docker-compose.yml` or the
    `Makefile` first (AC4, "variablerna MÅSTE dokumenteras"). Measured at
    authoring time, `.env.example` has no port variables at all."""
    pattern = re.compile(rf"(?m)^\s*#*\s*{re.escape(env_var)}\b")
    assert pattern.search(ENV_EXAMPLE_TEXT), (
        f"{ENV_EXAMPLE_PATH} does not mention {env_var} anywhere, so a developer reading it has "
        "no way to discover that this override exists.\n"
        f"--- {ENV_EXAMPLE_PATH.name} ---\n{ENV_EXAMPLE_TEXT}"
    )


def test_port_mapping_cases_cover_every_compose_port_env_var() -> None:
    """Given `_PORT_MAPPING_CASES`, when the set of `env_var`s it covers is
    compared against `COMPOSE_PORT_ENV_VARS`, then the two must match
    exactly. This documents, and locks in, that the parametrized compose
    guards above are not accidentally missing one of AC1/AC2's three
    variables -- a parametrized test with a silently narrower case list
    would report "no failures" for a variable it never actually checked."""
    covered = {case.env_var for case in _PORT_MAPPING_CASES}
    assert covered == set(COMPOSE_PORT_ENV_VARS), (
        f"expected the compose port-mapping cases to cover exactly {set(COMPOSE_PORT_ENV_VARS)}, "
        f"found {covered}"
    )
