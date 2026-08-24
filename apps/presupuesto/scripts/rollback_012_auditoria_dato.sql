-- rollback_012_auditoria_dato.sql — deshace 012.
--
-- Borra SÓLO lo que creó 012: la tabla y sus tres índices (los índices caen
-- con la tabla). No toca nada más — 012 no alteró ninguna estructura
-- existente, así que no hay nada que restaurar.
--
-- OJO: esto BORRA el rastro acumulado. Si ya hay filas, exportarlas antes:
--     \copy auditoria_dato TO 'auditoria_dato.csv' CSV HEADER

BEGIN;

DROP TABLE IF EXISTS auditoria_dato;

COMMIT;
