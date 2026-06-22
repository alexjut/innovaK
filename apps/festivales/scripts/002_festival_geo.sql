-- 002_festival_geo.sql
-- FEST-F-11 (QA): geolocalización del festival para representarlo como
-- marcador en el Mapa Kennedy.
--
-- Columnas aditivas nullable (sin pérdida de datos, reversible):
--   upl_codigo  → UPL de Kennedy (catálogo `upl`, referencia/filtro).
--   latitud/longitud → punto exacto (lo que ubica el marcador).
-- Solo se geolocaliza el festival que tenga lat/lon; los incompletos no
-- aparecen en el mapa (y no rompen nada).
--
-- Backfill: los 9 festivales actuales tienen lugar_texto y fechas en NULL,
-- así que no hay UPL previa que migrar. Las columnas quedan NULL.
--
-- Backup previo confirmado: poblacion_kennedy_diario.dump 2026-06-22 02:00 (<24h).

BEGIN;

ALTER TABLE festival ADD COLUMN IF NOT EXISTS upl_codigo SMALLINT NULL
    REFERENCES upl(codigo);
ALTER TABLE festival ADD COLUMN IF NOT EXISTS latitud  NUMERIC(9,6) NULL;
ALTER TABLE festival ADD COLUMN IF NOT EXISTS longitud NUMERIC(9,6) NULL;

CREATE INDEX IF NOT EXISTS idx_festival_geo
    ON festival (latitud, longitud) WHERE latitud IS NOT NULL;

COMMIT;
