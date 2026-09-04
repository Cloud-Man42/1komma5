# Phase 18 — Extended Timescale Compression

## Goal

Apply compression policies to all hypertables, not only `energy_readings`.

## Deliverables

| Hypertable | compress_after | segmentby |
|------------|----------------|-----------|
| `energy_readings` | 7 days | `site_id` |
| `consumer_samples` | 7 days | `consumer_id` |
| `vehicle_state_history` | 14 days | `vehicle_id` |

Collector slow lane task `timescale_compression` applies idempotently when `TIMESCALE_COMPRESSION_ENABLED=true`.
