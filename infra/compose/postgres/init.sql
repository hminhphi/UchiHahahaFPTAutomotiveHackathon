CREATE SCHEMA IF NOT EXISTS fleetiq;

CREATE TABLE IF NOT EXISTS fleetiq.schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO fleetiq.schema_migrations (version)
VALUES ('local-compose-v1')
ON CONFLICT (version) DO NOTHING;
