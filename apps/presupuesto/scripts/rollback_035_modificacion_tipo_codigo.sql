-- Rollback de 035. Quita el índice y la columna.
--
-- Seguro: la columna es derivada de `tipo`, que se queda. Lo que se pierde es
-- la llave estable para SQL, y con ella vuelve el riesgo de que una consulta
-- compare el literal del origen y devuelva un número más chico con cara de
-- correcto.

BEGIN;

DROP INDEX IF EXISTS idx_secop_mod_tipo_codigo;

ALTER TABLE secop_modificacion
    DROP COLUMN IF EXISTS tipo_codigo;

COMMIT;
