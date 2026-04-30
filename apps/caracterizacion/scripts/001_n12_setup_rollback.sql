-- ============================================================================
-- N12 — Rollback de 001_n12_setup.sql
-- ============================================================================
-- Solo usar si el setup falló o si se necesita revertir (ojo: si ya hay datos
-- nuevos en caracterizacion_*, este rollback los conserva pero pierde los
-- DEFAULTs y los UNIQUE quedan eliminados).
-- ============================================================================

BEGIN;

-- 6) Restaurar persona_id NULL en cultura
ALTER TABLE caracterizacion_cultura ALTER COLUMN persona_id DROP NOT NULL;

-- 5) Quitar firma_mongo_id
ALTER TABLE caracterizacion_salud DROP COLUMN IF EXISTS firma_mongo_id;

-- 4) Quitar evento_id e índices
DROP INDEX IF EXISTS idx_carac_salud_evento;
DROP INDEX IF EXISTS idx_carac_poblacional_evento;
DROP INDEX IF EXISTS idx_carac_partciud_evento;
ALTER TABLE caracterizacion_salud                    DROP COLUMN IF EXISTS evento_id;
ALTER TABLE caracterizacion_poblacional              DROP COLUMN IF EXISTS evento_id;
ALTER TABLE caracterizacion_participacion_ciudadana  DROP COLUMN IF EXISTS evento_id;

-- 3) Restaurar UNIQUE(persona_id) — falla si la tabla tiene duplicados
ALTER TABLE caracterizacion_cultura      ADD CONSTRAINT caracterizacion_cultura_persona_id_key      UNIQUE (persona_id);
ALTER TABLE caracterizacion_deporte      ADD CONSTRAINT caracterizacion_deporte_persona_id_key      UNIQUE (persona_id);
ALTER TABLE caracterizacion_mujer        ADD CONSTRAINT caracterizacion_mujer_persona_id_key        UNIQUE (persona_id);
ALTER TABLE caracterizacion_salud        ADD CONSTRAINT caracterizacion_salud_persona_id_key        UNIQUE (persona_id);
ALTER TABLE caracterizacion_poblacional  ADD CONSTRAINT caracterizacion_poblacional_persona_id_key  UNIQUE (persona_id);

-- 2) Borrar secuencias creadas
ALTER TABLE caracterizacion_cultura      ALTER COLUMN id DROP DEFAULT;
ALTER TABLE caracterizacion_deporte      ALTER COLUMN id DROP DEFAULT;
ALTER TABLE caracterizacion_mujer        ALTER COLUMN id DROP DEFAULT;
ALTER TABLE caracterizacion_salud        ALTER COLUMN id DROP DEFAULT;
ALTER TABLE caracterizacion_poblacional  ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE IF EXISTS caracterizacion_cultura_id_seq;
DROP SEQUENCE IF EXISTS caracterizacion_deporte_id_seq;
DROP SEQUENCE IF EXISTS caracterizacion_mujer_id_seq;
DROP SEQUENCE IF EXISTS caracterizacion_salud_id_seq;
DROP SEQUENCE IF EXISTS caracterizacion_poblacional_id_seq;

-- 1) Quitar selector de sector
ALTER TABLE evento DROP COLUMN IF EXISTS sector_caracterizacion;

COMMIT;
