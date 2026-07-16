-- Rollback de 011_geocodificacion_cache.sql
--
-- Seguro de correr: la tabla es una CACHÉ reconstruible. No hay dato original
-- aquí — todo se puede volver a pedir a Catastro corriendo
-- `asignar_estrato_org --por-direccion`. Nada más en la BD depende de ella
-- (no hay FKs entrantes: el estrato vive en inscripcion_banco_iniciativa).
--
-- Lo único que se pierde es tiempo: volver a geocodificar ~280 direcciones.

BEGIN;

DROP INDEX IF EXISTS idx_geocodificacion_cache_metodo;
DROP TABLE IF EXISTS geocodificacion_cache;

COMMIT;
