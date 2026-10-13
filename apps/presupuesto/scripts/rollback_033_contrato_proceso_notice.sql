-- Rollback de 033. Quita el índice y la columna.
--
-- Es seguro: la columna es derivada —sale de `url_proceso`, que se queda— así
-- que no se pierde ningún dato de la fuente. Lo que se pierde es la llave
-- materializada, y con ella cualquier cruce con el PAA que la use.

BEGIN;

DROP INDEX IF EXISTS idx_secop_contrato_notice;

ALTER TABLE secop_contrato
    DROP COLUMN IF EXISTS proceso_notice_id;

COMMIT;
