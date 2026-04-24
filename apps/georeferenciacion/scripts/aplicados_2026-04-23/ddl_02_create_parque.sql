-- =============================================================================
-- DDL C4.3d: Crear tabla parque
-- Fase del refactor mapa-kennedy
-- Fecha: 2026-04-23
-- Autor: alexjut + Claude Code
--
-- OBJETIVO:
-- Catálogo de parques en la BD, cargado desde parques.geojson (554 features).
-- El GeoJSON de disco queda como archivo fuente histórico; post-import el
-- endpoint leerá desde BD.
--
-- DISEÑO:
-- Columnas específicas para los campos más usados del GeoJSON (id_parque,
-- nombre, tipo, upz_codigo, localidad_codigo, area) + properties JSONB con
-- TODO el feature.properties para no perder info residual.
--
-- NOTA SOBRE EL CRS:
-- El archivo parques.geojson está en EPSG:3857 (Web Mercator, coords en
-- metros). El importer (import_02_parques.py) reproyecta a WGS84 antes del
-- INSERT — la columna geometry guarda SIEMPRE WGS84 para consistencia con
-- upz.geometry y barrio.geometry.
--
-- PRE-REQUISITOS:
-- - Backup reciente confirmado
-- - Tablas upz y localidad existentes (ya es así)
--
-- ROLLBACK:
--   DROP TABLE parque;
--
-- EJECUCIÓN:
--   psql -h 10.100.102.12 -U innova-bd -d poblacion_kennedy \
--        -f ddl_02_create_parque.sql
-- =============================================================================

BEGIN;

CREATE TABLE parque (
    id               SERIAL PRIMARY KEY,
    id_parque        TEXT UNIQUE,                                 -- Ej: '08-702'
    nombre           TEXT,                                        -- NOMBRE_PAR del geojson
    tipo             TEXT,                                        -- TIPOPARQUE (PARQUE DE BOLSILLO, etc.)
    estrato          SMALLINT,                                    -- ESTRATO (1-6, opcional)
    area             NUMERIC(14, 6),                              -- Area del feature
    upz_codigo       INTEGER REFERENCES upz(codigo) ON DELETE SET NULL,
    localidad_codigo INTEGER REFERENCES localidad(codigo) ON DELETE SET NULL,
    geometry         JSONB NOT NULL,                              -- Feature.geometry en WGS84
    properties       JSONB,                                       -- Feature.properties completo (fallback)
    fecha_incorp     DATE,                                        -- FECHAINCOR
    created_at       TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_parque_upz       ON parque(upz_codigo);
CREATE INDEX idx_parque_localidad ON parque(localidad_codigo);
CREATE INDEX idx_parque_tipo      ON parque(tipo);

COMMENT ON TABLE  parque                  IS 'Catálogo de parques de Bogotá (importado desde parques.geojson del IDRD)';
COMMENT ON COLUMN parque.id_parque        IS 'Código único de parque del IDRD (ej. 08-702 = Kennedy parque 702)';
COMMENT ON COLUMN parque.geometry         IS 'MultiPolygon en WGS84 (reproyectado desde EPSG:3857 del archivo original)';
COMMENT ON COLUMN parque.properties       IS 'Feature.properties completo del GeoJSON fuente (ADMINISTRA, CODIGOPOT, etc.)';

-- Verificación:
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'parque'
ORDER BY ordinal_position;

COMMIT;
