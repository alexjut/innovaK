-- Rollback de 013 — quita el PPT del catálogo.
--
-- Solo corre si NADIE lo está usando: el DELETE fallaría igual por las cuatro
-- FKs que apuntan a `tipo_documento`, pero es mejor decirlo antes y con un
-- mensaje que se entienda que dejar que reviente con un error de integridad.
--
-- Si ya hay personas registradas con PPT, este rollback NO es el camino:
-- habría que reasignarlas primero, y reasignarlas a «Otro» pierde el dato que
-- este script vino a conservar.

DO $$
DECLARE en_uso INTEGER;
BEGIN
    SELECT (SELECT count(*) FROM persona_documento WHERE tipo_documento_codigo = 7)
         + (SELECT count(*) FROM beneficiario       WHERE tipo_documento_codigo = 7)
         + (SELECT count(*) FROM crp                WHERE tipo_doc_bp_beneficiario_codigo = 7)
         + (SELECT count(*) FROM inscripcion_banco_iniciativa WHERE rep_tipo_doc_codigo = 7)
      INTO en_uso;
    IF en_uso > 0 THEN
        RAISE EXCEPTION 'Hay % registros usando el PPT: reasígnelos antes de quitarlo del catálogo.', en_uso;
    END IF;
    DELETE FROM tipo_documento WHERE codigo = 7;
END $$;
