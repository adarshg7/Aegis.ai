-- PostGIS & TimescaleDB are enabled in backend/app/core/database.py via init_db()
-- This script runs BEFORE the app starts and handles any manual setup.

-- Enable extensions (redundant safety)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- The tables are created by SQLAlchemy (Base.metadata.create_all)
-- After tables exist, convert accident_events to TimescaleDB hypertable:
-- (This is idempotent — safe to run multiple times)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'accident_events')
     AND NOT EXISTS (SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_name = 'accident_events')
  THEN
    PERFORM create_hypertable('accident_events', 'detected_at', if_not_exists => TRUE);
    RAISE NOTICE 'TimescaleDB hypertable created for accident_events';
  END IF;
END $$;

-- Create spatial index helper function for nearby queries
CREATE OR REPLACE FUNCTION accidents_within_radius(
  center_lat DOUBLE PRECISION,
  center_lon DOUBLE PRECISION,
  radius_km  DOUBLE PRECISION
)
RETURNS TABLE (
  id UUID,
  detected_at TIMESTAMPTZ,
  severity TEXT,
  confidence_score DOUBLE PRECISION,
  distance_km DOUBLE PRECISION
)
LANGUAGE SQL STABLE AS $$
  SELECT
    ae.id,
    ae.detected_at,
    ae.severity::TEXT,
    ae.confidence_score,
    ST_Distance(
      ae.location::geography,
      ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326)::geography
    ) / 1000.0 AS distance_km
  FROM accident_events ae
  WHERE ST_DWithin(
    ae.location::geography,
    ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326)::geography,
    radius_km * 1000
  )
  ORDER BY ae.detected_at DESC
  LIMIT 500;
$$;
