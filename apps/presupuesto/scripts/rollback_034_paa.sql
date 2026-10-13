-- Rollback de 034. Borra las tres tablas del espejo del PAA.
--
-- DESTRUCTIVO: se pierde el espejo entero. No se pierde nada irrecuperable —los
-- dos datasets de origen siguen publicados y la ingesta los vuelve a bajar en
-- unos minutos—, pero sí se pierde el histórico de `synced_at`, o sea cuándo
-- vimos cambiar cada fila.
--
-- En orden inverso: la tabla de procesos primero, que es la que referencia.

BEGIN;

DROP TABLE IF EXISTS paa_item_proceso;
DROP TABLE IF EXISTS paa_item;
DROP TABLE IF EXISTS paa_encabezado;

COMMIT;
