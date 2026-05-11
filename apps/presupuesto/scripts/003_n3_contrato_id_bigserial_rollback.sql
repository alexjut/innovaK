-- Rollback de 003_n3_contrato_id_bigserial.sql
-- Solo correr si hay que revertir N3 y aún no se han creado dependencias
-- externas sobre las columnas `id` (otras FKs apuntando, etc.).

BEGIN;

ALTER TABLE contrato_proyecto DROP CONSTRAINT IF EXISTS contrato_proyecto_id_key;
ALTER TABLE contrato_proyecto DROP COLUMN IF EXISTS id;
DROP SEQUENCE IF EXISTS contrato_proyecto_id_seq;

ALTER TABLE contrato_actividad DROP CONSTRAINT IF EXISTS contrato_actividad_id_key;
ALTER TABLE contrato_actividad DROP COLUMN IF EXISTS id;
DROP SEQUENCE IF EXISTS contrato_actividad_id_seq;

COMMIT;
