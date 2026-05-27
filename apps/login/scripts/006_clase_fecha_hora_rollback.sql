-- Rollback de 006_clase_fecha_hora.sql
-- ─────────────────────────────────────────────────────────────────────────

BEGIN;

DROP INDEX IF EXISTS ix_clase_evento_fecha;

ALTER TABLE clase DROP COLUMN IF EXISTS lugar;
ALTER TABLE clase DROP COLUMN IF EXISTS hora_fin;
ALTER TABLE clase DROP COLUMN IF EXISTS hora_inicio;
ALTER TABLE clase DROP COLUMN IF EXISTS fecha;

COMMIT;
