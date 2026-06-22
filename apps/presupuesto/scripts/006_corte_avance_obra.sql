-- 006_corte_avance_obra.sql
-- Seguimiento minucioso de obra por CORTES. Un corte registra el avance en un
-- momento dado y aplica a:
--   - un CONTRATO completo  (objeto_tipo='contrato')  -> caso interventoría.
--   - una VÍA / tramo       (objeto_tipo='tramo').
--   - un PARQUE intervenido (objeto_tipo='parque').
-- Cada corte: fecha, %, observación, evidencia (foto cifrada en Mongo) y autor.
-- Es el historial auditable de "cómo va cada cosa en el tiempo".
-- Backup previo: poblacion_kennedy_diario.dump 2026-06-22 02:00 (<24h).

BEGIN;

CREATE TABLE IF NOT EXISTS corte_avance_obra (
    id            BIGSERIAL PRIMARY KEY,
    contrato_id   INTEGER NOT NULL REFERENCES contrato(id),
    objeto_tipo   VARCHAR(10) NOT NULL,          -- contrato | tramo | parque
    objeto_id     BIGINT NULL,                   -- id del tramo/intervención (NULL si contrato)
    fecha         DATE NOT NULL,
    pct           SMALLINT NOT NULL DEFAULT 0,
    observacion   TEXT NULL,
    foto_antes_mongo_id   VARCHAR(64) NULL,      -- evidencia "antes" (cifrada en Mongo, reducida)
    foto_despues_mongo_id VARCHAR(64) NULL,      -- evidencia "después"
    autor_id      INTEGER NULL,                  -- usuario que reportó
    created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_corte_obra_contrato ON corte_avance_obra (contrato_id);
CREATE INDEX IF NOT EXISTS idx_corte_obra_objeto   ON corte_avance_obra (objeto_tipo, objeto_id);

COMMIT;
