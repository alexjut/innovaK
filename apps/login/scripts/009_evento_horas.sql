-- 009_evento_horas.sql
-- GEN-F-02 (QA Fase 1): horario de la actividad data-driven por tipo.
--
-- Contexto: evento.fecha_inicio/fecha_fin son DATE (sin componente de hora).
-- Hay actividades que necesitan hora de inicio/fin para citar gente
-- (ej. una clase, una entrega con cita). Se agregan columnas TIME aditivas
-- (nullable, sin romper otros sistemas que leen `evento`) y un flag en
-- tipo_evento que decide si el formulario las pide (igual que
-- requiere_actividad_plan).
--
-- Backup previo confirmado: poblacion_kennedy_diario.dump 2026-06-22 02:00 (<24h).

BEGIN;

ALTER TABLE evento      ADD COLUMN IF NOT EXISTS hora_inicio TIME NULL;
ALTER TABLE evento      ADD COLUMN IF NOT EXISTS hora_fin    TIME NULL;
ALTER TABLE tipo_evento ADD COLUMN IF NOT EXISTS requiere_horario boolean NOT NULL DEFAULT false;

-- Tipos que típicamente citan a hora fija. Ajustable por UI luego.
UPDATE tipo_evento SET requiere_horario = true
 WHERE codigo IN ('CURSO', 'CAPACITACION', 'ENTREGA');

COMMIT;
