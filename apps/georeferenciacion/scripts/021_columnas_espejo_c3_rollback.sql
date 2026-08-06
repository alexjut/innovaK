-- Rollback de 021_columnas_espejo_c3.sql
--
-- Devuelve las 6 tablas al subconjunto de columnas espejo que tenían antes.
-- Es seguro en el sentido estricto —solo borra columnas que agregó el 021 y
-- que nadie tenía antes—, pero ojo: si algún sync ya corrió con --write
-- después del 021, este rollback **descarta** los hashes y las marcas de
-- sincronización que hubiera escrito. Los datos de la fuente en sí no se
-- pierden: viven en las columnas de siempre.
--
-- No borra `fecha_fuente` de manzana_estrato, sector_catastral ni
-- barrio_legalizado: esas tres ya la tenían antes del 021.

BEGIN;

ALTER TABLE colegio_sede       DROP COLUMN IF EXISTS hash_fila;
ALTER TABLE cai                DROP COLUMN IF EXISTS hash_fila;

ALTER TABLE placa_domiciliaria DROP COLUMN IF EXISTS fuente;
ALTER TABLE placa_domiciliaria DROP COLUMN IF EXISTS hash_fila;

ALTER TABLE manzana_estrato    DROP COLUMN IF EXISTS synced_at;
ALTER TABLE manzana_estrato    DROP COLUMN IF EXISTS fuente;
ALTER TABLE manzana_estrato    DROP COLUMN IF EXISTS hash_fila;

ALTER TABLE sector_catastral   DROP COLUMN IF EXISTS synced_at;
ALTER TABLE sector_catastral   DROP COLUMN IF EXISTS fuente;
ALTER TABLE sector_catastral   DROP COLUMN IF EXISTS hash_fila;

ALTER TABLE barrio_legalizado  DROP COLUMN IF EXISTS synced_at;
ALTER TABLE barrio_legalizado  DROP COLUMN IF EXISTS fuente;
ALTER TABLE barrio_legalizado  DROP COLUMN IF EXISTS hash_fila;

COMMIT;
