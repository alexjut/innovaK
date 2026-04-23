-- =============================================================================
-- DDL C4.3e: Crear tabla escuela
-- Fase del refactor mapa-kennedy
-- Fecha: 2026-04-23
-- Autor: alexjut + Claude Code
--
-- OBJETIVO:
-- Catálogo definitivo de escuelas/puntos de atención en Kennedy, cargado
-- desde escuelas.csv (242 rows, con tipos 'Cultura'/'Deporte' legibles).
-- La tabla actual escuelas_staging queda como snapshot original; se puede
-- eliminar post-validación.
--
-- HALLAZGO DEL ANÁLISIS:
-- - escuelas_staging y escuelas.csv tienen los mismos 242 registros.
-- - staging.tipo usa códigos numéricos ('1'=Cultura, '2'=Deporte) —
--   coincide con catálogo tipo_punto (1=Cultura, 2=Deporte).
-- - CSV trae tipos legibles. Se prefiere CSV como fuente para claridad.
-- - No existen escuelas tipo 'Educación' en los datos reales.
--
-- DISEÑO:
-- - tipo TEXT (valores 'Cultura'/'Deporte'; sin CHECK constraint para
--   permitir futuras categorías sin DDL).
-- - FKs a upz/barrio/localidad quedan nullable — el CSV solo tiene
--   coordenadas y dirección, no códigos. Se pueden llenar después
--   con geolocalización inversa o manualmente.
-- - Columna origen para trazabilidad del import ('csv' | 'staging' | 'manual').
--
-- PRE-REQUISITOS:
-- - Backup reciente confirmado
-- - Tablas upz, barrio, localidad existentes (ya es así)
--
-- ROLLBACK:
--   DROP TABLE escuela;
--
-- EJECUCIÓN:
--   psql -h 10.100.102.12 -U innova-bd -d poblacion_kennedy \
--        -f ddl_03_create_escuela.sql
-- =============================================================================

BEGIN;

CREATE TABLE escuela (
    id                SERIAL PRIMARY KEY,
    nombre            TEXT NOT NULL,
    tipo              TEXT,                                         -- 'Cultura' | 'Deporte' | ...
    direccion         TEXT,
    latitud           NUMERIC(9, 6),
    longitud          NUMERIC(9, 6),
    localidad_codigo  INTEGER REFERENCES localidad(codigo) ON DELETE SET NULL,
    upz_codigo        INTEGER REFERENCES upz(codigo) ON DELETE SET NULL,
    barrio_codigo     INTEGER REFERENCES barrio(codigo) ON DELETE SET NULL,
    origen            TEXT DEFAULT 'csv',                           -- 'csv' | 'staging' | 'manual'
    activo            BOOLEAN DEFAULT TRUE,
    created_at        TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_escuela_tipo      ON escuela(tipo);
CREATE INDEX idx_escuela_localidad ON escuela(localidad_codigo);
CREATE INDEX idx_escuela_upz       ON escuela(upz_codigo);
CREATE INDEX idx_escuela_barrio    ON escuela(barrio_codigo);

COMMENT ON TABLE  escuela         IS 'Catálogo de escuelas (cultura/deporte) de la Alcaldía de Kennedy';
COMMENT ON COLUMN escuela.tipo    IS 'Categoría: Cultura | Deporte. Coincide con tipo_punto.nombre pero no es FK para tolerar valores libres.';
COMMENT ON COLUMN escuela.origen  IS 'Trazabilidad del import: csv (fuente primaria) | staging | manual';

-- Verificación:
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'escuela'
ORDER BY ordinal_position;

COMMIT;
