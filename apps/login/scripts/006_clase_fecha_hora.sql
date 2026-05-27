-- ─────────────────────────────────────────────────────────────────────────
-- 006 — Agregar fecha/hora/lugar a `clase` (PR-B módulo Curso Docente)
-- ─────────────────────────────────────────────────────────────────────────
-- Fecha: 2026-05-27
-- Contexto: el schema legacy modela `clase` como "molde recurrente" con
-- las fechas reales en `asistencia_clase`. La decisión del proyecto
-- ("Coordinador crea N sesiones planeadas al crear el curso") requiere
-- que `clase` represente "una sesión con su fecha". Estas columnas son
-- aditivas, nullable, sin impacto en datos existentes (tabla vacía).
--
-- Backup: poblacion_kennedy_pre_sesiones_20260527_162525.dump
-- Rollback: en 006_clase_fecha_hora_rollback.sql
-- ─────────────────────────────────────────────────────────────────────────

BEGIN;

ALTER TABLE clase ADD COLUMN IF NOT EXISTS fecha DATE;
ALTER TABLE clase ADD COLUMN IF NOT EXISTS hora_inicio TIME;
ALTER TABLE clase ADD COLUMN IF NOT EXISTS hora_fin TIME;
ALTER TABLE clase ADD COLUMN IF NOT EXISTS lugar TEXT;

-- Índice para listar sesiones de un evento ordenadas por fecha.
CREATE INDEX IF NOT EXISTS ix_clase_evento_fecha ON clase (evento_id, fecha);

COMMIT;
