-- rollback 005
BEGIN;
ALTER TABLE intervencion_parque DROP COLUMN IF EXISTS direccion;
COMMIT;
