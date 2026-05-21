-- ============================================================================
-- 002_fix_puente_id.sql
-- Fix: agregar `id BIGSERIAL UNIQUE` a entrega_beca_elemento
-- ============================================================================
-- Fecha:    2026-05-21
-- Motivo:   Django no soporta modelos con PK compuesta. Sin una columna
--           `id` única, INSERT ... RETURNING id falla con:
--           "column entrega_beca_elemento.id does not exist".
--           Mismo patrón que Banco usa en `inscripcion_banco_escenario`.
-- Tabla:    entrega_beca_elemento (puente M2M EntregaBeca ↔ ElementoDotacion)
-- Impacto:  tabla recién creada, sin filas en momento del fix.
-- ============================================================================

BEGIN;

ALTER TABLE entrega_beca_elemento
  ADD COLUMN id BIGSERIAL UNIQUE;

COMMIT;

-- Verificación:
-- \d entrega_beca_elemento
-- Esperar: id bigint NOT NULL DEFAULT nextval(...) + unique constraint
