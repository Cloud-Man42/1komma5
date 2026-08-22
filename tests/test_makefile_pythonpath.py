"""Tests for the Makefile's `PYTHONPATH` assignment (GH-12).

`Makefile:2` reads::

    PYTHONPATH := backend:collector:packages/energy-core/src

This *looks* like it configures the `PYTHONPATH` every recipe below runs
with, but GNU Make only forwards a variable into a recipe's shell if that
variable came from the calling environment, was set on the `make` command
line, or was explicitly marked with `export`. None of those apply to this
line, so every recipe's subshell sees an empty `PYTHONPATH` regardless of
it -- the assignment is dead weight that misleads anyone debugging a
`ModuleNotFoundError` into thinking this line is responsible for module
resolution, when it does nothing at all.

Module resolution for the workspace packages (`energy_core`, `app.main`,
`app.collector`) actually works through an entirely different mechanism:
the editable installs (`.pth` files) that `uv sync --all-packages` writes
into the project's virtual environment. That mechanism does not need
`PYTHONPATH` to be set at all.

Two outcomes fix this and both are accepted here:

1. Mark the assignment with `export` so it genuinely reaches every
   recipe's subshell, or
2. Delete the line, since nothing actually depends on it.

What is not accepted is the current state: a `PYTHONPATH` assignment that
is present but not exported. `test_makefile_pythonpath_assignment_is_exported_to_recipes_or_absent`
below checks this by literally running `make` against the real Makefile
and reading back what a recipe's own shell sees for `$PYTHONPATH`, rather
than pattern-matching for the `export` keyword -- so it is agnostic to
*which* of the two accepted fixes lands, and to whether `export` is
written on the same line as the assignment or on a separate line.

`test_python_recipe_resolves_workspace_modules_without_makefiles_pythonpath`
checks the property that actually matters in practice: that a
Python-running Makefile recipe, executed exactly as `make` executes it
(with no exported `PYTHONPATH` reaching its subshell, matching today's
reality), can still import `energy_core`, `app.main` and `app.collector`.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE_PATH = REPO_ROOT / "Makefile"

_MAKE_BINARY = shutil.which("make")

# Matches a line assigning a value to PYTHONPATH via any of GNU Make's
# assignment operators (`=`, `:=`, `?=`, `+=`, `!=`), with or without a
# leading `export` keyword. Deliberately does not try to decide, from the
# text alone, whether the assignment is "really" exported -- that question
# is answered behaviorally by `_run_probe_target`, not by this regex.
PYTHONPATH_ASSIGNMENT_RE = re.compile(r"^(?:export\s+)?PYTHONPATH\s*[:+?!]?=", re.MULTILINE)

# The workspace packages GH-13 established must be importable after
# `uv sync --all-packages`: `energy-core`'s top-level package, and the
# backend/collector submodules of the `app` namespace package they both
# contribute to (see tests/test_workspace_install.py for why the
# submodules, not a bare `import app`, are the right check).
WORKSPACE_IMPORT_TARGETS = ["energy_core", "app.main", "app.collector"]


def _run_probe_target(
    tmp_path: Path, target: str, recipe_command: str
) -> subprocess.CompletedProcess[str]:
    """Define `target` as a Make target with a single recipe line running
    `recipe_command`, in a throwaway wrapper Makefile that `include`s the
    real repository Makefile, then run `make <target>` and return the
    result.

    `include`-ing the real Makefile (rather than copying or re-parsing it)
    means `$(UV)` and every other variable it defines resolve exactly as
    they do for `make install`, `make test`, etc. Running the probe through
    a real `make` invocation, rather than reimplementing GNU Make's export
    rules in Python, is what lets these tests observe Make's actual,
    authoritative answer instead of a second-guessed approximation of it.

    `PYTHONPATH` is deliberately removed from the subprocess environment
    before invoking `make`, so the only possible source of a non-empty
    `PYTHONPATH` inside the recipe is the Makefile's own `export` (or lack
    thereof) -- not something leaking in from the environment this test
    itself happens to run in.
    """
    wrapper_path = tmp_path / "probe.mk"
    wrapper_path.write_text(
        f"include {MAKEFILE_PATH}\n\n.PHONY: {target}\n{target}:\n\t{recipe_command}\n",
        encoding="utf-8",
    )

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    return subprocess.run(
        ["make", "--no-print-directory", "-f", str(wrapper_path), "-C", str(REPO_ROOT), target],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_makefile_pythonpath_assignment_is_exported_to_recipes_or_absent(tmp_path: Path) -> None:
    """Given the Makefile, when it contains a PYTHONPATH assignment, then
    that assignment must actually reach recipe subshells -- verified by
    running `make` against the real Makefile and reading back what a
    recipe's own shell sees for `$PYTHONPATH`. A PYTHONPATH assignment that
    is present but not exported is strictly worse than no assignment at
    all: it looks like it configures every recipe's PYTHONPATH but
    silently never does, misleading anyone debugging a module-resolution
    error into the wrong file. Both "no PYTHONPATH assignment at all" and
    "an exported PYTHONPATH assignment" are accepted outcomes; only an
    unexported-but-present assignment is not."""
    if _MAKE_BINARY is None:
        pytest.skip("make is not on PATH; cannot exercise the Makefile's recipe environment.")

    content = MAKEFILE_PATH.read_text(encoding="utf-8")
    if not PYTHONPATH_ASSIGNMENT_RE.search(content):
        return  # No assignment at all is an accepted outcome; nothing further to verify.

    probe = _run_probe_target(
        tmp_path,
        "_pythonpath_export_probe",
        '@echo "PYTHONPATH_IN_RECIPE=[$$PYTHONPATH]"',
    )
    assert probe.returncode == 0, (
        f"Probe recipe exited with {probe.returncode}.\n--- stdout ---\n{probe.stdout}\n"
        f"--- stderr ---\n{probe.stderr}"
    )

    marker_match = re.search(r"PYTHONPATH_IN_RECIPE=\[(.*)\]", probe.stdout)
    assert marker_match, (
        f"Probe recipe did not print the expected marker.\n--- stdout ---\n{probe.stdout}"
    )

    assert marker_match.group(1) != "", (
        f"{MAKEFILE_PATH} assigns a value to PYTHONPATH, but a real `make` recipe's shell "
        "sees an empty PYTHONPATH (GNU Make only forwards a variable into a recipe's shell "
        "if it came from the environment, was set on the command line, or was marked with "
        "'export' -- none of which applies here). The assignment looks like it configures "
        "every recipe's PYTHONPATH but silently never does. Either mark it with 'export' so "
        "recipes genuinely receive it, or delete the line entirely -- a present-but-"
        "unexported assignment is not an accepted outcome."
    )


@pytest.mark.parametrize("import_target", WORKSPACE_IMPORT_TARGETS)
def test_python_recipe_resolves_workspace_modules_without_makefiles_pythonpath(
    tmp_path: Path, import_target: str
) -> None:
    """Given the Makefile's variable definitions (via `$(UV)`), when a
    recipe that runs Python is executed exactly as `make` executes it -- in
    a subshell that receives no exported PYTHONPATH, matching what every
    real recipe subshell sees today -- then each workspace module
    (energy_core, app.main, app.collector) must still be importable. This
    holds regardless of whether Makefile:2's PYTHONPATH assignment is
    exported or removed: module resolution here works through the editable
    installs `uv sync --all-packages` creates, not through PYTHONPATH, so a
    Python-running recipe's ability to resolve these modules must not be
    allowed to depend on that line."""
    if _MAKE_BINARY is None:
        pytest.skip("make is not on PATH; cannot exercise a Makefile recipe.")
    if shutil.which("uv") is None:
        pytest.skip("uv is not on PATH; cannot exercise a Python-running Makefile recipe.")

    probe = _run_probe_target(
        tmp_path,
        "_module_resolution_probe",
        f'$(UV) run python -c "import {import_target}"',
    )

    assert probe.returncode == 0, (
        f'A `make` recipe running `$(UV) run python -c "import {import_target}"` failed '
        f"(module {import_target!r} is not importable via the mechanism Makefile recipes "
        f"actually rely on for module resolution).\n--- stdout ---\n{probe.stdout}\n"
        f"--- stderr ---\n{probe.stderr}"
    )
