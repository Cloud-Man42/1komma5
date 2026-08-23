"""Synthetic validation of the shared `tsc` diagnostic-line parser (GH-32
prevention pattern, applied to issue #17's typecheck-script work).

See `tests/_tsc_diagnostics.py`'s module docstring for why this parsing
logic lives in its own module rather than as a second, drift-prone copy
inside `tests/test_frontend_vitest_globals_typecheck.py` and
`tests/test_frontend_typecheck_script.py`.

What this module does NOT cover
--------------------------------
This module never invokes the real `tsc` binary and never reads any file
under `frontend/`. It only feeds `tsc_diagnostics` hand-written strings
shaped like real `tsc --pretty false` output. The real-compiler-output
checks live in `tests/test_frontend_vitest_globals_typecheck.py`
(`test_tsc_reports_no_vitest_global_name_errors`) and
`tests/test_frontend_typecheck_script.py`
(`test_npm_run_typecheck_matches_direct_tsc_invocation`), both of which skip
where `frontend/node_modules/.bin/tsc` is absent.
"""

from __future__ import annotations

import pytest
from _tsc_diagnostics import tsc_diagnostics

# Real single-line diagnostic header captured from this repository's own
# `frontend/node_modules/.bin/tsc --noEmit --pretty false` output at
# authoring time (issue #55's pre-existing TS2741 in a test fixture).
_REAL_SINGLE_LINE_DIAGNOSTIC = (
    "src/components/EnergyChart.test.tsx(11,9): error TS2741: Property "
    "'correction_factor' is missing in type '{ timestamp: string; "
    "baseline_power_w: number; }' but required in type 'SolarForecastPoint'."
)

# Real multi-line diagnostic captured the same way (issue #55's TS2345 in
# api.extended.test.ts): tsc indents a continuation line explaining exactly
# which properties are missing. `TSC_DIAGNOSTIC_RE` is line-anchored, so
# only the header line is expected to match.
_REAL_MULTI_LINE_DIAGNOSTIC = (
    "src/lib/api.extended.test.ts(216,27): error TS2345: Argument of type "
    "'{ connection_type: \"local\"; host: string; port: number; }' is not "
    "assignable to parameter of type 'HeartbeatConfigUpdate'.\n"
    "  Type '{ connection_type: \"local\"; host: string; port: number; }' is "
    "missing the following properties from type 'HeartbeatConfigUpdate': "
    "use_tls, api_path, poll_interval_seconds, dashboard_refresh_seconds, "
    "and 2 more."
)


def test_tsc_diagnostics_parses_a_single_line_diagnostic() -> None:
    """Given a single, real-shaped `tsc --pretty false` diagnostic header
    line, when it is parsed, then exactly one diagnostic dict must be
    returned with the path, line, column, code, and message pulled out
    correctly."""
    diagnostics = tsc_diagnostics(_REAL_SINGLE_LINE_DIAGNOSTIC)
    assert len(diagnostics) == 1
    assert diagnostics[0]["path"] == "src/components/EnergyChart.test.tsx"
    assert diagnostics[0]["line"] == "11"
    assert diagnostics[0]["column"] == "9"
    assert diagnostics[0]["code"] == "TS2741"
    assert diagnostics[0]["message"].startswith("Property 'correction_factor'")


def test_tsc_diagnostics_skips_indented_continuation_lines() -> None:
    """Given a real multi-line diagnostic (a header line followed by an
    indented continuation line, as `tsc` emits for TS2345), when it is
    parsed, then only the header line must be reported as a diagnostic --
    the continuation line does not match the line-anchored pattern and must
    be silently skipped rather than mis-parsed as a second diagnostic."""
    diagnostics = tsc_diagnostics(_REAL_MULTI_LINE_DIAGNOSTIC)
    assert len(diagnostics) == 1
    assert diagnostics[0]["code"] == "TS2345"
    assert diagnostics[0]["path"] == "src/lib/api.extended.test.ts"


def test_tsc_diagnostics_returns_multiple_diagnostics_in_document_order() -> None:
    """Given output containing two independent diagnostic header lines, when
    it is parsed, then both must be returned, in the order they appeared."""
    combined = f"{_REAL_SINGLE_LINE_DIAGNOSTIC}\n{_REAL_MULTI_LINE_DIAGNOSTIC}\n"
    diagnostics = tsc_diagnostics(combined)
    assert [d["code"] for d in diagnostics] == ["TS2741", "TS2345"]


@pytest.mark.parametrize(
    "output",
    [
        pytest.param("", id="empty_string"),
        pytest.param("Found 4 errors in 3 files.\n", id="summary_line_only"),
        pytest.param(
            "src/lib/brand.ts:12:5 - error TS6133: 'unused' is declared but never read.\n",
            id="differently_formatted_diagnostic_is_not_matched",
        ),
    ],
)
def test_tsc_diagnostics_returns_nothing_for_unmatched_output(output: str) -> None:
    """Given output containing no line matching the expected `tsc --pretty
    false` diagnostic-header shape (empty output, a bare summary line, or a
    diagnostic formatted differently -- e.g. `tsc`'s default pretty-printed
    style, which this module's regex deliberately does not attempt to
    parse), when it is parsed, then an empty list must be returned rather
    than a false match."""
    assert tsc_diagnostics(output) == []
