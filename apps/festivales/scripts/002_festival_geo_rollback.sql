-- 002_festival_geo_rollback.sql — revierte 002_festival_geo.sql

BEGIN;

DROP INDEX IF EXISTS idx_festival_geo;
ALTER TABLE festival DROP COLUMN IF EXISTS upl_codigo;
ALTER TABLE festival DROP COLUMN IF EXISTS latitud;
ALTER TABLE festival DROP COLUMN IF EXISTS longitud;

COMMIT;
