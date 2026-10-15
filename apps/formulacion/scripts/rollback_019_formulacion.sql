-- rollback_019_formulacion.sql — retira el dominio Formulación.
--
-- ABORTA si hay alguna formulación cargada. Un DROP pelado se llevaría por
-- delante el expediente entero —requisitos, documentos y el vínculo con los
-- contratos— sin dejar rastro, y por CASCADE, en silencio.
--
-- Para ver qué hay antes de decidir:
--   SELECT id, vigencia, objeto FROM formulacion ORDER BY id;

BEGIN;

DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM formulacion;
    IF n > 0 THEN
        RAISE EXCEPTION
            'No se puede retirar el dominio: hay % formulación(es) cargada(s). '
            'Exportalas o cancelalas primero.', n;
    END IF;
END $$;

DROP TABLE IF EXISTS formulacion_contrato;
DROP TABLE IF EXISTS formulacion_requisito_cumplido;
DROP TABLE IF EXISTS formulacion_documento;
DROP TABLE IF EXISTS formulacion_requisito;
DROP TABLE IF EXISTS formulacion;
DROP TABLE IF EXISTS formulacion_transicion;
DROP TABLE IF EXISTS formulacion_estado;

COMMIT;
