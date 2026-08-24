-- Deshace 010_etapa_contrato.sql. Se pierde lo que se haya registrado.
BEGIN;
DROP INDEX IF EXISTS idx_contrato_etapa;
ALTER TABLE contrato
    DROP CONSTRAINT IF EXISTS contrato_etapa_codigo_fkey,
    DROP CONSTRAINT IF EXISTS contrato_etapa_usuario_fkey,
    DROP COLUMN IF EXISTS etapa_codigo,
    DROP COLUMN IF EXISTS etapa_fecha,
    DROP COLUMN IF EXISTS etapa_usuario_id;
DROP TABLE IF EXISTS etapa_contrato;
COMMIT;
