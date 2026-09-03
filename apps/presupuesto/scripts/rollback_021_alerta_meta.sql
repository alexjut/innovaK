-- Rollback del 021. Columnas nuevas sobre una tabla existente: se dropean
-- las cuatro y el índice que dependía de ellas se va solo con la columna.
BEGIN;
ALTER TABLE presu_presupuesto_meta_vigencia
    DROP COLUMN IF EXISTS alerta,
    DROP COLUMN IF EXISTS magnitud_contratada,
    DROP COLUMN IF EXISTS magnitud_ejecutada,
    DROP COLUMN IF EXISTS cumplimiento_pct;
COMMIT;
