-- Rollback de 012_placa_domiciliaria.sql
--
-- Seguro de correr: la tabla es una COPIA de una capa pública de Catastro. No
-- hay dato original acá — todo se vuelve a bajar con `manage.py sync_placas`.
-- Nada más en la BD depende de ella (sin FKs entrantes: las direcciones
-- capturadas guardan su propio texto + lon/lat en su tabla).
--
-- Lo único que se pierde es tiempo: ~1 h de re-sincronización.

BEGIN;

DROP INDEX IF EXISTS idx_placa_via;
DROP INDEX IF EXISTS idx_placa_via_placa;
DROP INDEX IF EXISTS idx_placa_via_kennedy;
DROP TABLE IF EXISTS placa_domiciliaria;

COMMIT;
