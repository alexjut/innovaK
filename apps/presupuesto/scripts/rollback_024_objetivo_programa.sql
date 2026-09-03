-- Rollback del 024 · objetivo estratégico y programa
--
-- Aditivo, así que el rollback es limpio: `metas.objetivo_estrategico`,
-- `codprog` y `nomprog` nunca se tocaron, y al soltar `metas.programa_id` todo
-- vuelve a leerse del texto como antes.
--
-- ORDEN: primero la columna de `metas` (referencia a `presu_programa`),
-- después el programa (referencia al objetivo), y al final el objetivo. Al
-- revés, cada DROP chocaría con la FK del de abajo.

BEGIN;

ALTER TABLE metas DROP CONSTRAINT IF EXISTS fk_metas_programa;
DROP INDEX IF EXISTS idx_metas_programa_id;
ALTER TABLE metas DROP COLUMN IF EXISTS programa_id;

DROP TABLE IF EXISTS presu_programa;
DROP TABLE IF EXISTS presu_objetivo_estrategico;

COMMIT;
