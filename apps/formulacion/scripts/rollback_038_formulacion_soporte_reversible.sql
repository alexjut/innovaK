-- Rollback de 038. Quita la baja lógica.
--
-- ⚠ VUELVE AL BORRADO DESTRUCTIVO. Tras esto, un DELETE de soporte destruye la
-- fila y el blob sin vuelta, que es el defecto 3.3. Y las filas que estaban
-- dadas de baja reaparecen como vivas: el listado las vuelve a mostrar y
-- vuelven a contar como evidencia de su requisito, porque el filtro que las
-- escondía desaparece con la columna.
--
-- Antes de correrlo, revisar qué hay dado de baja:
--     SELECT id, formulacion_id, nombre_archivo, eliminado_en, eliminado_motivo
--     FROM formulacion_documento WHERE eliminado_en IS NOT NULL;

BEGIN;

ALTER TABLE formulacion_documento
    DROP CONSTRAINT IF EXISTS ck_formulacion_doc_baja;

DROP INDEX IF EXISTS idx_formulacion_doc_vivos;

ALTER TABLE formulacion_documento
    DROP COLUMN IF EXISTS eliminado_en,
    DROP COLUMN IF EXISTS eliminado_por_id,
    DROP COLUMN IF EXISTS eliminado_motivo;

COMMIT;
