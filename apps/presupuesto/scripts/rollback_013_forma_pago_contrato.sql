-- rollback_013_forma_pago_contrato.sql — deshace 013.
--
-- OJO: BORRA las formas de pago que hayan capturado las áreas. Exportarlas
-- antes si hacen falta:
--   \copy (SELECT id, forma_pago_codigo FROM contrato WHERE forma_pago_codigo IS NOT NULL) TO 'fp.csv' CSV HEADER
--
-- El catálogo `forma_pago` NO se borra entero: ya existía antes de 013. Sólo
-- se quitan las filas 901+, que son las que 013 sembró.

BEGIN;

ALTER TABLE contrato DROP CONSTRAINT IF EXISTS contrato_forma_pago_fk;
ALTER TABLE contrato DROP COLUMN IF EXISTS forma_pago_usuario_id;
ALTER TABLE contrato DROP COLUMN IF EXISTS forma_pago_fecha;
ALTER TABLE contrato DROP COLUMN IF EXISTS forma_pago_codigo;

DELETE FROM forma_pago WHERE codigo BETWEEN 901 AND 999;

COMMIT;
