-- EMIC TimescaleDB retention policies (NOT APPLIED — review before execution)
-- Run manually after backup and capacity review.

-- Raw energy readings: keep 90 days
-- SELECT add_retention_policy('energy_readings', INTERVAL '90 days');

-- Consumer samples: keep 90 days
-- SELECT add_retention_policy('consumer_samples', INTERVAL '90 days');

-- Vehicle state history: keep 180 days
-- SELECT add_retention_policy('vehicle_state_history', INTERVAL '180 days');

-- Hourly rollups: keep 730 days (2 years)
-- SELECT add_retention_policy('energy_hourly', INTERVAL '730 days');

-- Daily rollups: keep indefinitely (no retention policy)

-- Compression (automated in Phase 12 when TIMESCALE_COMPRESSION_ENABLED=true):
-- ALTER TABLE energy_readings SET (timescaledb.compress, timescaledb.compress_segmentby = 'site_id');
-- SELECT add_compression_policy('energy_readings', INTERVAL '7 days');
