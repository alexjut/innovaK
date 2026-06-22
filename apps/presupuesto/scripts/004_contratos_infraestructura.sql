-- 004_contratos_infraestructura.sql
-- Ingesta de contratos de infraestructura (subgrupo Infraestructura) + sus
-- vías (tramos) y parques de obra para el Mapa Kennedy.
--
-- Decisiones de Alex (2026-06-22):
--   - Campos infra como columnas nuevas en `contrato` (tabla compartida).
--   - Parques: REUSAR la tabla `parque` existente (los 13 ya están, con
--     geometría). Solo se crea el puente `intervencion_parque`.
--   - Tramos viales: tabla nueva con geom GeoJSON cacheado desde la Malla Vial.
--
-- Backup previo confirmado: poblacion_kennedy_diario.dump 2026-06-22 02:00 (<24h).
-- Todo aditivo y reversible (ver _rollback).

BEGIN;

-- 1) Campos infra en la tabla contrato (aditivos, nullable).
ALTER TABLE contrato ADD COLUMN IF NOT EXISTS categoria              VARCHAR(20)   NULL;
ALTER TABLE contrato ADD COLUMN IF NOT EXISTS proyecto_codigo        VARCHAR(10)   NULL;
ALTER TABLE contrato ADD COLUMN IF NOT EXISTS proyecto_nombre        TEXT          NULL;
ALTER TABLE contrato ADD COLUMN IF NOT EXISTS ejecucion              SMALLINT      NULL;
ALTER TABLE contrato ADD COLUMN IF NOT EXISTS interventoria_contrato VARCHAR(30)   NULL;
ALTER TABLE contrato ADD COLUMN IF NOT EXISTS interventoria_valor    NUMERIC(18,4) NULL;

-- 2) Tramos viales del contrato (geom = LineString GeoJSON cacheado por CIV).
CREATE TABLE IF NOT EXISTS tramo_vial_contrato (
    id                 BIGSERIAL PRIMARY KEY,
    contrato_id        INTEGER NOT NULL REFERENCES contrato(id),
    civ                BIGINT  NULL,
    pk_id              BIGINT  NULL,
    eje_vial           TEXT    NULL,
    desde              TEXT    NULL,
    hasta              TEXT    NULL,
    valor_intervencion NUMERIC(18,4) NULL,
    pct_avance         SMALLINT DEFAULT 0,
    geom               JSONB   NULL,
    geo_status         VARCHAR(15) NOT NULL DEFAULT 'PENDIENTE',  -- OK / NO_ENCONTRADO / FALLBACK / PENDIENTE
    created_at         TIMESTAMPTZ DEFAULT now(),
    updated_at         TIMESTAMPTZ DEFAULT now(),
    UNIQUE (contrato_id, civ)
);
CREATE INDEX IF NOT EXISTS idx_tramo_vial_contrato     ON tramo_vial_contrato (contrato_id);
CREATE INDEX IF NOT EXISTS idx_tramo_vial_geo_status   ON tramo_vial_contrato (geo_status);

-- 3) Intervención de parque por contrato (reusa `parque` existente).
--    El parque es único; lo que se repite es la intervención por contrato
--    (caso 08-742 en COP-816 y CON-993).
CREATE TABLE IF NOT EXISTS intervencion_parque (
    id          BIGSERIAL PRIMARY KEY,
    parque_id   INTEGER NOT NULL REFERENCES parque(id),
    contrato_id INTEGER NOT NULL REFERENCES contrato(id),
    pct_avance  SMALLINT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (parque_id, contrato_id)
);
CREATE INDEX IF NOT EXISTS idx_intervencion_parque_contrato ON intervencion_parque (contrato_id);

COMMIT;
