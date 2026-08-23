# Security Policy

## Reporting a vulnerability

Report privately, through this repository's GitHub Security Advisories form:

**<https://github.com/L0rdS474n/1komma5/security/advisories/new>**

Private vulnerability reporting is enabled on this repository, so that form is
open to anyone with a GitHub account. A report filed through it stays visible
only to you and the maintainer until an advisory is published.

Please do not open a public issue, pull request or comment to report a security
vulnerability, and do not publish a working exploit before a fix is available.
Public disclosure of a defect in this project can expose stored third-party
credentials and remote control of physical hardware — see *What is at stake*
below.

If you cannot use the form for some reason, say so in a message that contains no
technical detail (for example by opening an empty draft advisory), and a private
channel will be arranged.

## What to include

The more of this you can provide, the faster the fix:

- What the flaw is, and which component it is in — backend endpoint, collector,
  frontend, `energy-core` package, charger adapter, deployment configuration.
- How to reproduce it, step by step, including the request or input that
  triggers it.
- What an attacker gains: read access to stored credentials, control of a
  device, denial of service, data corruption.
- Which commit or branch you tested against, and your environment (Python
  version, Node version, Docker or native).
- Any suggested fix, if you have one.

Redact real credentials from anything you paste. Send the shape of the token,
not the token.

## What is at stake

This is not a read-only dashboard. Two properties should raise your severity
estimate for anything you find:

**It stores third-party credentials at rest.** The database schema holds a
1Komma5 Heartbeat account password and its renewed bearer token
(`HeartbeatSettingsModel.password`, `HeartbeatSettingsModel.api_token`), a
ChargeAmps API key per charger (`EvChargerModel.chargeamps_api_key`), and an
Arctic Spa API key (`SpaDeviceConfigModel.api_key`). A flaw that leaks database
rows, log lines or error payloads can therefore hand over live accounts on
someone else's service, not just data belonging to this application.

**It actuates physical hardware.** The backend exposes endpoints that write to
EV charging equipment (`backend/app/api/ev_chargers.py`, including the charging
override) and to a spa (`backend/app/api/spa.py`), and the documented Arctic Spa
API controls temperature, pumps, lights, filtration and heating. An
authorization or injection flaw on those paths is not only a data problem: it
can start or stop charging, or change the state of hardware in someone's home.

Treat anything touching credential storage, credential logging, the charger
adapters or the site-scoped authorization checks as high severity by default.

## Supported versions

The project has no releases and no version tags. Only the current `main` branch
is supported, and fixes land there. Docker images are built from a checkout, so
redeploy from an updated `main` to pick up a fix.

## What happens after you report

This repository is maintained by one person, so response times are best effort
rather than contractual. What you can expect:

1. Acknowledgement of the report through the advisory thread.
2. Confirmation or rejection, with the reasoning stated.
3. A fix on `main`, together with a regression test that fails without it.
4. A published advisory crediting you, unless you ask to stay anonymous.

If a report turns out not to be a security problem, it will be redirected to the
public tracker as an ordinary defect, with your agreement.

## Hardening already in place

Reported flaws are triaged against what the repository already does:

- **Secret scanning and push protection** are enabled, so a credential pushed to
  this repository is blocked or flagged. The only environment files under
  version control are the four examples (`.env.example`,
  `.env.development.example`, `.env.production.example` and
  `frontend/.env.local.example`), and `.gitignore` excludes `.env` and
  `.env.local`.
- **Dependabot security updates** are enabled, and
  [`.github/dependabot.yml`](.github/dependabot.yml) additionally schedules
  version updates for the `uv` workspace, the `npm` frontend and the GitHub
  Actions workflows.
- **`main` is protected**: pull request required, force pushes and deletions
  blocked, linear history enforced.

A finding that one of these controls does not actually hold is itself worth
reporting through the private form above.
