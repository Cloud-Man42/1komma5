# Phase 17 — Admin Audit Log

## Goal

Track admin configuration mutations with redacted summaries.

## Deliverables

- `admin_audit_log` table (migration 061)
- `GET /api/admin/audit-log` — admin token required
- Audit hooks on: heartbeat config, sites CRUD/energy-config, energy control settings/apply
- Redaction of passwords/tokens in summaries
