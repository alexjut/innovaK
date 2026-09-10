-- Rollback del 028. Devuelve las dos llaves a como estaban.
--
-- OJO: si la base ya trae más de una fila de `tercero_sap` para el mismo
-- (tipo_doc, num_doc) —que es exactamente lo que el 028 vino a permitir— el
-- índice viejo NO se puede recrear. En ese caso hay que decidir con qué fila
-- quedarse ANTES de correr esto, y ese es el trabajo que el 028 evita.

BEGIN;

DROP INDEX IF EXISTS uq_tercero_sap_doc_bp;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM tercero_sap
               GROUP BY tipo_doc, num_doc HAVING count(*) > 1) THEN
        RAISE EXCEPTION
            'Hay documentos con mas de un tercero: el indice viejo no cabe. '
            'Decide con cual quedarte antes de revertir.';
    END IF;
END $$;

ALTER TABLE tercero_sap
    ADD CONSTRAINT uq_tercero_sap_doc UNIQUE (tipo_doc, num_doc);

ALTER TABLE crp ALTER COLUMN n_interno_crp DROP NOT NULL;
ALTER TABLE crp ALTER COLUMN n_posicion_crp DROP NOT NULL;

COMMIT;
