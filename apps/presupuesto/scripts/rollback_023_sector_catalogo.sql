-- Rollback del 023 · catálogo de SECTOR
--
-- El 023 es aditivo, así que el rollback también es limpio: nada de lo que
-- existía antes se tocó. `metas.sector` (texto) nunca se modificó, así que al
-- soltar `metas.sector_id` la pantalla vuelve exactamente al estado anterior
-- —con el gráfico partido incluido—.
--
-- ORDEN: primero la columna de `metas` (que referencia el catálogo), después
-- las tablas. Al revés, el DROP de `presu_sector` chocaría con la FK.
-- `presu_sector_alias` cae por CASCADE de su propia FK, pero se suelta
-- explícito para no depender de eso.

BEGIN;

ALTER TABLE metas DROP CONSTRAINT IF EXISTS fk_metas_sector;
DROP INDEX IF EXISTS idx_metas_sector_id;
ALTER TABLE metas DROP COLUMN IF EXISTS sector_id;

DROP TABLE IF EXISTS presu_sector_alias;
DROP TABLE IF EXISTS presu_sector;

COMMIT;
