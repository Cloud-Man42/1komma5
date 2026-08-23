# Contributing to EMIC

Thanks for wanting to help. This document describes how work actually happens in
this repository — the setup flow that works, the branch and commit conventions
in use, the protection rules on `main`, and the two things a new contributor
here will otherwise trip over: a red CI pipeline and an upstream that rewrites
its history.

Everything below was measured against this repository. Where a rule is enforced
by a machine, that is said explicitly; where it is a convention, that is said
too.

- Code, comments, commit messages and documentation are written in English.
- Discussion in the issue tracker is often in Swedish. Either language is fine
  in an issue or a pull request comment.

## Before you start: an issue first

Every change starts from an issue. The issue states the problem, the measured
evidence for it, and the acceptance criteria; the pull request then satisfies
those criteria and nothing else.

Issues are grouped into milestones:

- **`Runda 1 — kodgenomgång 2026-08-22`** is **frozen**. No new issues are added
  to it. It is finished when every issue in it is closed.
- **`Runda 2 — nya fynd`** is where new findings go, including findings you make
  while fixing something in Runda 1.

If you discover a second, unrelated defect while working on an issue, open a new
issue in Runda 2 for it and leave it alone. Do not widen the pull request you
are working on. The one exception is the *same* defect appearing in another
place in the same change — fixing all of its occurrences is a single objective,
not two.

## Development setup

### Prerequisites

- **Python 3.12+** — every `pyproject.toml` in the workspace declares
  `requires-python = ">=3.12"`.
- **[uv](https://docs.astral.sh/uv/)** — the workspace is a uv workspace with a
  single `uv.lock` at the repository root.
- **Node.js 20.9 or newer** — `frontend/package.json` declares
  `engines.node = "^20.9.0 || >=21.1.0"`. The two gaps that range leaves
  (20.0–20.8 and 21.0) are not arbitrary: they are exactly the versions
  `eslint`'s own `engines.node` (`^18.18.0 || ^20.9.0 || >=21.1.0`)
  excludes. No `.npmrc` sets `engine-strict`, so npm
  warns with `EBADENGINE` on an unsupported runtime rather than refusing to
  install — treat that warning as an error.
  `.nvmrc` at the repository root pins **26.4.0**, the version development
  happens on; `nvm use` from anywhere in the tree picks it up, because nvm walks
  upward looking for the file. CI runs Node 22.
- **make** (optional — every target is a one-line shell command you can run by
  hand; see below).

### From a clean clone

```bash
git clone git@github.com:L0rdS474n/1komma5.git
cd 1komma5

cp .env.development.example .env
cp frontend/.env.local.example frontend/.env.local

make install
make migrate
make seed
```

`make install` runs two commands:

```bash
uv sync --all-packages
cd frontend && npm ci
```

**The `--all-packages` flag is not optional.** The root project
(`energy-monorepo`) has an empty `[project] dependencies` list, so a bare
`uv sync` installs only that empty root plus the `dev` dependency group. It does
*not* install the workspace members `packages/energy-core`, `backend` and
`collector`, and without them the application and the test suite fail with
`ModuleNotFoundError`. This was GH-13; `tests/test_workspace_install.py` and
`tests/test_markdown_install_instructions_all_packages.py` now hold every
surface that documents or runs the install to the flag, including this file.

Module resolution comes from the editable installs that `uv sync --all-packages`
writes into `.venv` as `.pth` files. Do not add a `PYTHONPATH` assignment to the
`Makefile` to compensate — a plain Make variable is not exported into a recipe's
subshell, so it silently does nothing (GH-12).

The default local database is SQLite (`energy-dev.db` in the project root), and
the collector runs against a mock provider. No Docker, PostgreSQL or third-party
credentials are needed for development. See [`README.md`](README.md) for running
the three processes and for the Docker production path.

## Running the tests

```bash
make test
```

which is:

```bash
uv run pytest
cd frontend && npm test
```

Useful subsets:

| Command | Scope |
|---|---|
| `uv run pytest -m "not integration"` | What CI runs |
| `uv run pytest -m integration` | Requires PostgreSQL/TimescaleDB (`make test-integration`) |
| `uv run pytest tests/` | Repository-level guard tests only |
| `cd frontend && npm test` | Vitest, once |
| `cd frontend && npm run test:coverage` | Vitest with coverage |

Windows without make: `.\test-windows.ps1`.

**Measure the baseline before you change anything.** Run both suites on your
branch point and write the numbers down, so that after your change you can show
that the delta is exactly what you intended and nothing else moved.

### CI is currently red on `main` — GH-37

The `Tests` workflow (`.github/workflows/test.yml`) has two jobs, `python` and
`frontend`. The `python` job **fails on `main` today**, and has failed on every
commit since the current base.

The cause is known and is not your pull request: two tests in
`backend/tests/test_solar_forecast_api.py` call `enable_solar_config` one line
outside the `patch(...)` block that is supposed to mock the weather provider, so
they reach `api.open-meteo.com` for real. A developer machine has outgoing
network and they pass; a GitHub runner does not, and they fail with
`httpx.ConnectTimeout`. This is tracked as GH-37 and is fixed there, not here.

What this means for your pull request:

- A red `python` job does **not** automatically mean you broke something.
  Compare the failure list against the two known failures above before you start
  debugging.
- CI is **not** a required status check in branch protection, so a red run does
  not mechanically block a merge. That makes the human check the gate: say in
  the pull request which tests you ran locally and what they returned.
- Once GH-37 lands, required status checks can be turned on. Until then, do not
  treat green CI as achievable, and do not write it into a checklist as if it
  were.

## Branches and commits

Branch names follow `<type>/<issue-number>-<slug>`:

```
fix/13-uv-sync-all-packages
fix/16-node-version-pinning
docs/19-contribution-infrastructure
```

`<type>` is the same vocabulary as the commit subject: `fix`, `feat`, `docs`,
`build`, `refactor`, `test`, `ci`, `chore`.

Commit messages follow Conventional Commits in the subject, explain *why* in the
body, and close their issue on the last line:

```
fix(build): install workspace members in the install flow

`uv sync` at the workspace root installs only the root project, whose
[project] dependencies list is empty, plus the dev group. The workspace
members are left out, so `import app` fails ...

Closes #13
```

`Closes #N` is what links the pull request to its issue and closes the issue on
merge. Verify after merging that the issue actually closed — a typo in the
reference fails silently.

Keep commits few, small and independent. That is not only review hygiene here:
see the upstream section below for why it is also what keeps a resync cheap.

## Pull requests

`main` is protected. Measured from the branch protection API:

| Rule | State |
|---|---|
| Pull request required to change `main` | yes |
| Required approving reviews | 0 |
| Stale reviews dismissed on new commits | yes |
| Conversation resolution required before merge | yes |
| Linear history required | yes — **merge commits are rejected** |
| Force pushes to `main` | blocked |
| Branch deletion | blocked |
| Required status checks | none configured (see GH-37) |
| Code-owner review required | no |
| Rules enforced for admins | no — the repository owner can bypass; you cannot |

Because linear history is required, merge with **squash** or **rebase**. A merge
commit will be refused.

`.github/CODEOWNERS` assigns @L0rdS474n as the owner of every path, so pull
requests request review from that account automatically. Since code-owner review
is not currently required by branch protection, that is a review *request*, not
a merge gate.

One pull request, one objective. Fill in
[`.github/pull_request_template.md`](.github/pull_request_template.md) — it is
the Definition of Done in checklist form. In particular:

- **Ship the tests with the change.** Every change merged into this base so far
  added or extended tests in the same commit: GH-13 added
  `tests/test_workspace_install.py`, GH-12 added
  `tests/test_makefile_pythonpath.py`, GH-14 added
  `tests/test_makefile_collector_dev_directory.py`, GH-16 added
  `tests/test_frontend_node_version_pinning.py`. A test that fails before your
  change and passes after it is the evidence that the change did something.
- **Report real numbers.** Paste what the suites printed, not "tests pass".
- **Keep new code lint-clean.** `uv run ruff format --check <paths>` and
  `uv run ruff check <paths>` must be clean for the files you touched. The
  repository as a whole is not yet clean; that pre-existing debt is tracked
  separately and is not yours to fix in an unrelated pull request.
- **Never commit a secret.** Only `.env*.example` files are tracked; `.env` and
  `.env.local` are ignored. Secret scanning and push protection are enabled on
  this repository, so a pushed credential will be caught — but by then it has
  left your machine and must be rotated. See [`SECURITY.md`](SECURITY.md).

## The upstream fork model — GH-25

This repository is a fork of
[`Cloud-Man42/1komma5`](https://github.com/Cloud-Man42/1komma5), and syncing with
it is not ordinary fork maintenance. Read this before your first resync.

**Upstream squashes everything into a single commit and force-pushes it.**
`git rev-list --count upstream/master` is `1`: the whole project is one commit
there, replaced wholesale on every publish.

Right after a resync the two are related. Today `main` is rooted directly on
upstream's tip — `git merge-base main upstream/master` and
`git rev-list --max-parents=0 main` both return the same commit, and GitHub's
compare API reports this fork as simply *ahead*. That is the good state, and it
is the state a resync restores.

The next force-push ends it. Upstream's replacement commit shares no ancestry
with anything in this tree, so `git merge-base` returns nothing and the compare
API answers `No common ancestor` — exactly what GH-25 measured when it last
happened. `git merge` and `git rebase` both need that ancestor, so from then on
neither works, and the resync below is the only way back.

The model that does work:

> **`main` = the current upstream commit, with our patches replayed on top,
> re-based whenever upstream drifts.**

When drift is detected:

1. `git fetch upstream`
2. Tag the current state as a backup — the operation must be reversible.
   (`backup/pre-upstream-sync/*` tags from earlier syncs are still in the repo.)
3. `git reset --hard upstream/master`
4. Cherry-pick our commits, in order.
5. **Re-measure the whole baseline on the new base.** Never assume it carried
   over. GH-25 measured the last drift at 109 files, +7767/-1430; a rewrite of
   that size moves behaviour, not just line numbers.
6. `git push --force-with-lease origin main`

Consequences you should plan for:

- **Check for drift before starting an issue**, not after. `git fetch upstream`
  and compare. A force-push mid-session otherwise means you keep building on
  abandoned code.
- **Line numbers quoted in issues go stale** across a resync. Search for the
  named function, constant or exact phrase instead of trusting a line number.
- **Your branch may need re-basing onto a rewritten `main`.** Small, independent
  commits are cheap to replay; one large squashed change is not.

## Security

Do not report a vulnerability through the issue tracker. Use the private channel
described in [`SECURITY.md`](SECURITY.md). This project stores third-party
credentials and controls physical hardware, so please read that document before
reporting.

## Code of Conduct

Participation is governed by [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## License

The project is licensed under Apache-2.0 ([`LICENSE`](LICENSE),
[`NOTICE`](NOTICE)). By contributing, you agree that your contribution is
licensed under the same terms.
