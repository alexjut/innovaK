-- Rollback de 005_curso_sesiones_secuencias.sql
-- Restaura el estado pre-PR-A: id sin DEFAULT, sin secuencias propias,
-- sin índices nuevos.
-- ─────────────────────────────────────────────────────────────────────────

BEGIN;

-- Quitar DEFAULT y dueño antes de borrar secuencias
ALTER TABLE clase ALTER COLUMN id DROP DEFAULT;
ALTER TABLE horario_clase ALTER COLUMN id DROP DEFAULT;
ALTER TABLE asistencia_clase ALTER COLUMN id DROP DEFAULT;
ALTER TABLE grupo ALTER COLUMN id DROP DEFAULT;

DROP SEQUENCE IF EXISTS clase_id_seq;
DROP SEQUENCE IF EXISTS horario_clase_id_seq;
DROP SEQUENCE IF EXISTS asistencia_clase_id_seq;
DROP SEQUENCE IF EXISTS grupo_id_seq;

DROP INDEX IF EXISTS ux_asistencia_clase_participante_fecha;
DROP INDEX IF EXISTS ix_clase_evento;
DROP INDEX IF EXISTS ix_horario_clase;
DROP INDEX IF EXISTS ix_asistencia_clase_fecha;
DROP INDEX IF EXISTS ix_asistencia_participante;
DROP INDEX IF EXISTS ix_evaluacion_evento;
DROP INDEX IF EXISTS ix_evaluacion_participante;

COMMIT;
