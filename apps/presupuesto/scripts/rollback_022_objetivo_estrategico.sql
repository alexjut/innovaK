-- Rollback del 022. Columna nueva sobre una tabla existente.
BEGIN;
ALTER TABLE metas DROP COLUMN IF EXISTS objetivo_estrategico;
COMMIT;
