-- =============================================================================
-- DDL C4.3c: Agregar columna geometry JSONB a upz y barrio
-- Fase del refactor mapa-kennedy (rama feat/mapa-kennedy-dashboard)
-- Fecha: 2026-04-23
-- Autor: alexjut + Claude Code
--
-- OBJETIVO:
-- Permitir que los polígonos de UPZ y Barrios vivan en BD (en vez de solo
-- en archivos Upz.geojson y barrios_kennedy.geojson del disco). Con la
-- columna en JSONB, los endpoints podrán leer desde BD y retirar la
-- dependencia de los archivos (opción B del análisis — sin PostGIS).
--
-- AFECTA:
-- - Tabla upz: +1 columna, nullable (se rellena con import_01_geometries.py)
-- - Tabla barrio: +1 columna, nullable
-- - Cero downtime: los endpoints actuales siguen funcionando desde disco
--   hasta que se corra el importer y se actualice el JS/view.
--
-- PRE-REQUISITOS:
-- - Backup reciente (<24h). Confirmado: poblacion_kennedy_diario.dump 2026-04-23 02:00
-- - Permisos DDL en el usuario innova-bd sobre esquema public.
--
-- ROLLBACK (si falla el import posterior o se necesita revertir):
--   BEGIN;
--   ALTER TABLE upz    DROP COLUMN geometry;
--   ALTER TABLE barrio DROP COLUMN geometry;
--   COMMIT;
--
-- EJECUCIÓN:
--   psql -h 10.100.102.12 -U innova-bd -d poblacion_kennedy \
--        -f ddl_01_geometry_upz_barrio.sql
-- =============================================================================

BEGIN;

ALTER TABLE upz    ADD COLUMN geometry JSONB;
ALTER TABLE barrio ADD COLUMN geometry JSONB;

COMMENT ON COLUMN upz.geometry    IS 'Feature.geometry (MultiPolygon) de la UPZ en WGS84/EPSG:4686. NULL si aún no se importó.';
COMMENT ON COLUMN barrio.geometry IS 'Feature.geometry (MultiPolygon) del barrio en WGS84. NULL si aún no se importó.';

-- Verificación (aún dentro de la transacción — si algo falla, hacer ROLLBACK):
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('upz', 'barrio')
  AND column_name = 'geometry'
ORDER BY table_name;

-- Si la verificación muestra las 2 filas esperadas, commitear:
COMMIT;
