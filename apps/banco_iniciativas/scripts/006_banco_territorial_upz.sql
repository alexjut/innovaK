-- ============================================================================
-- Banco de Iniciativas #62 — Territorial M-01 (Opción A: UPL + UPZ coexisten)
-- Fecha: 2026-06-30 · Rama: feat/banco-qa-#62
--
-- Deportes confirmó: UPL (9 oficiales) y UPZ (12 oficiales) son DOS listas
-- INDEPENDIENTES, no reemplazo. Se REUSA la tabla `upz` existente
-- (georeferenciación, 12 UPZ de Kennedy + geometría) — NO se crea catálogo nuevo.
-- `upl` se conserva intacto (9 activas). Solo se agrega un puntero en la
-- inscripción al UPZ elegido, junto al `upl_codigo` que ya existe.
--
-- 100% aditivo: una columna nullable. NO toca las 24 inscripciones (quedan
-- con upz_codigo NULL). Idempotente (IF NOT EXISTS). NO LO CORRE CLAUDE: lo
-- corre Alex tras snapshot.
--
-- OJO ORDEN DE DESPLIEGUE: el modelo Django agrega el campo `upz` (FK), así que
-- toda query sobre inscripcion_banco_iniciativa pasará a seleccionar upz_codigo.
-- Corre este ALTER ANTES de reiniciar el contenedor con el código nuevo.
-- ============================================================================

BEGIN;

ALTER TABLE inscripcion_banco_iniciativa
    ADD COLUMN IF NOT EXISTS upz_codigo INTEGER REFERENCES upz(codigo);

COMMIT;

-- ============================================================================
-- ROLLBACK
-- ============================================================================
-- ALTER TABLE inscripcion_banco_iniciativa DROP COLUMN IF EXISTS upz_codigo;
