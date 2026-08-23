<!--
One pull request, one objective. If this change fixes a second, unrelated
finding, open a separate issue in the "Runda 2 — nya fynd" milestone instead of
widening this pull request. See CONTRIBUTING.md.
-->

## What this changes

<!-- One or two sentences. What is different after this merges? -->

Closes #

## Why

<!-- The defect or need, and the evidence for it. Link the issue's measurement
rather than repeating it. -->

## Evidence

Paste what the commands printed. Numbers, not adjectives.

```text
uv run pytest            before:            after:
cd frontend && npm test  before:            after:
```

<!--
CI is red on `main` today (GH-37): two tests in
backend/tests/test_solar_forecast_api.py reach api.open-meteo.com, which a
GitHub runner cannot. If the `python` job fails here, check the failure list
against those two before debugging.
-->

## Checklist

- [ ] The pull request has a single objective, and the diff contains nothing
      unrelated to it.
- [ ] An issue exists for this change and is referenced with `Closes #N` in the
      commit message.
- [ ] Tests ship with the change: at least one test that fails before it and
      passes after it.
- [ ] Both suites were run locally and their output is pasted above.
- [ ] `uv run ruff format --check` and `uv run ruff check` are clean for the
      files this change touches.
- [ ] Boundary inputs are validated, and errors are handled rather than
      swallowed.
- [ ] No credential, token or private host name in the code, tests, logs, error
      messages or this description.
- [ ] Documentation that describes the changed behaviour was updated in this
      same change (`README.md`, `CONTRIBUTING.md`, `docs/`).
- [ ] The branch is named `<type>/<issue-number>-<slug>` and will be merged with
      squash or rebase — `main` requires linear history and rejects merge
      commits.

## Risk

<!-- What could this break, and what would tell you it did? Say "none" only if
you can name why. -->
