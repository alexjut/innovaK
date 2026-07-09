-- ============================================================================
-- Estratificación IDECA — DDL
-- Propuesta: docs/propuestas/estratificacion_ideca.md
--
-- NO aplicar contra poblacion_kennedy sin: (1) backup < 24h, (2) confirmación
-- de Alex. La SECCIÓN A es segura (tablas/columnas nuevas, no toca datos ajenos)
-- y basta para el backend shapely. La SECCIÓN B (PostGIS) requiere además el
-- visto bueno del dueño de infra (CREATE EXTENSION es superusuario, afecta a
-- TODA la base compartida) — ver riesgo R1 de la propuesta.
-- ============================================================================

-- ─────────────────────────────────────────────────────────────────────────
-- SECCIÓN A — Base (JSONB). Suficiente para el backend shapely. Sin PostGIS.
-- ─────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS manzana_estrato (
    id             BIGSERIAL PRIMARY KEY,          -- secuencia desde el día 1 (no MAX+1)
    codigo_manzana TEXT NOT NULL UNIQUE,
    estrato        SMALLINT,                       -- 0/NULL = sin estrato oficial
    geometry       JSONB NOT NULL,                 -- polígono GeoJSON (fuente canónica)
    properties     JSONB,
    fecha_fuente   DATE,                           -- vigencia del dato en Catastro
    created_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_manzana_estrato_estrato ON manzana_estrato (estrato);

-- Estrato oficial de la sede (calculado por point-in-polygon). NO reemplaza el
-- estrato autodeclarado de la organización (vive en inscripcion_banco_iniciativa).
ALTER TABLE escuela ADD COLUMN IF NOT EXISTS estrato_ideca SMALLINT;

-- ─────────────────────────────────────────────────────────────────────────
-- SECCIÓN B — PostGIS (OPCIONAL). Aplicar SOLO tras visto bueno de infra.
-- Habilita el backend 'postgis' (ST_Contains server-side). El backend shapely
-- sigue funcionando sin esto; esta sección es una optimización de velocidad.
-- ─────────────────────────────────────────────────────────────────────────

-- 1) Extensión (superusuario; afecta toda la BD). Recomendado en esquema propio:
--    CREATE SCHEMA IF NOT EXISTS postgis;
--    CREATE EXTENSION IF NOT EXISTS postgis SCHEMA postgis;
-- CREATE EXTENSION IF NOT EXISTS postgis;

-- 2) Columna geométrica derivada del JSONB + índice espacial.
-- ALTER TABLE manzana_estrato ADD COLUMN IF NOT EXISTS geom geometry(MultiPolygon, 4326);
-- UPDATE manzana_estrato
--    SET geom = ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(geometry::text), 4326))
--  WHERE geom IS NULL;
-- CREATE INDEX IF NOT EXISTS idx_manzana_estrato_geom ON manzana_estrato USING GIST (geom);

-- ─────────────────────────────────────────────────────────────────────────
-- ROLLBACK (SECCIÓN A)
-- ─────────────────────────────────────────────────────────────────────────
-- ALTER TABLE escuela DROP COLUMN IF EXISTS estrato_ideca;
-- DROP TABLE IF EXISTS manzana_estrato;
