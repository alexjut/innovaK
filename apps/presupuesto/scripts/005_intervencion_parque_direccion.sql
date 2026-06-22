-- 005_intervencion_parque_direccion.sql
-- El form de alta de parques captura CÓDIGO, DIRECCIÓN, NOMBRE, % AVANCE.
-- código/nombre vienen de la tabla `parque`; la dirección de la intervención
-- (planilla del contrato) no se guardaba → columna aditiva, nullable, reversible.
-- Backup previo: poblacion_kennedy_diario.dump 2026-06-22 02:00 (<24h).

BEGIN;
ALTER TABLE intervencion_parque ADD COLUMN IF NOT EXISTS direccion TEXT NULL;
COMMIT;
