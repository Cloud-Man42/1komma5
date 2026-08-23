"""Shared parsing of `tsc --pretty false` diagnostic output (GH-32 prevention).

Two different acceptance criteria need to turn raw `tsc --noEmit --pretty
false` stdout into a structured list of `{path, line, column, code,
message}` diagnostics:

1. Issue #21's `tests/test_frontend_vitest_globals_typecheck.py`
   (`test_tsc_reports_no_vitest_global_name_errors`), which checks that no
   diagnostic names one of Vitest's injected globals.
2. Issue #17 (this repository's CI-hardening work)'s
   `tests/test_frontend_typecheck_script.py`, which compares the diagnostic
   set `npm run typecheck` reports against the diagnostic set a direct
   `frontend/node_modules/.bin/tsc --noEmit` invocation reports.

Before this module existed, `_tsc_diagnostics` and `_TSC_DIAGNOSTIC_RE` were
defined privately inside `tests/test_frontend_vitest_globals_typecheck.py`
only. Issue #32 is exactly this shape of bug: `tests/test_markdown_install_instructions_all_packages.py`
and `tests/test_contribution_governance_docs.py` each carried their own copy
of a `uv sync`-detection regex, and the two copies silently drifted apart
(one recognized a shape the other missed). `tests/_uv_sync_command_scan.py`
is that duplication's fix -- a single shared module both guards import from
-- and this module follows the exact same precedent for the `tsc`
diagnostic-line regex, before a second copy has a chance to exist at all.
"""

from __future__ import annotations

import re

# Matches one `tsc --pretty false` diagnostic header line, e.g.:
#   src/lib/brand.test.ts(3,1): error TS2582: Cannot find name 'describe'.
# `tsc` may follow this with further, differently-indented continuation
# lines for multi-part messages (observed for TS2345, which appends an
# indented "Type '...' is missing the following properties..." line); those
# simply do not match this line-anchored pattern and are skipped, which is
# fine here since every diagnostic class either caller cares about (TS2304,
# TS2582, and -- for the direct-vs-npm comparison in
# `tests/test_frontend_typecheck_script.py` -- every code the project
# currently produces) is fully described by its own single header line.
TSC_DIAGNOSTIC_RE = re.compile(
    r"^(?P<path>[^():]+)\((?P<line>\d+),(?P<column>\d+)\): error (?P<code>TS\d+): (?P<message>.*)$"
)


def tsc_diagnostics(output: str) -> list[dict[str, str]]:
    """Return every `tsc --pretty false` diagnostic header line in `output`
    that matches `TSC_DIAGNOSTIC_RE`, each as a `{path, line, column, code,
    message}` dict, in the order they appear in `output`."""
    diagnostics = []
    for line in output.splitlines():
        match = TSC_DIAGNOSTIC_RE.match(line)
        if match:
            diagnostics.append(match.groupdict())
    return diagnostics
