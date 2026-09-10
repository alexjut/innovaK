-- 028 · Las dos llaves naturales del CRP, que hoy no imponen nada
--
-- POR QUÉ. Los dos defectos aparecen SOLO en el segundo corte, y los dos
-- escriben datos equivocados sin un mensaje de error.
--
-- 1. `uq_crp_interno_posicion` es único sobre dos columnas NULLABLE. En
--    Postgres dos NULL no chocan dentro de un índice único, así que una fila
--    con «N° Interno CRP» vacío nunca dispara el `ON CONFLICT` del cargador:
--    el corte siguiente la INSERTA otra vez en vez de actualizarla. Con doce
--    cortes quedan doce copias del mismo compromiso, once marcadas
--    `vigente=FALSE` —que los endpoints nuevos esconden y `metrics` sumaba—,
--    y `filas_insertadas` cuenta como nueva cada mes la misma posición.
--    Medido: 0 de las 2.630 filas del corte 2026-09-07 vienen sin llave, así
--    que el NOT NULL no pierde nada. `validar()` frena el archivo antes, con
--    el número de fila del Excel a la vista.
--
-- 2. `uq_tercero_sap_doc` llavea al tercero por (tipo_doc, num_doc), y el
--    documento NO identifica al tercero: `899999061` es el NIT de Bogotá D.C.
--    y en el archivo lo llevan SIETE entidades distritales con siete business
--    partners de SAP distintos (3, 103, 117, 119, 122, 126, 137). Las siete
--    colapsaban en una fila y ganaba el nombre de la última leída del Excel:
--    19 filas de CRP por $34.771 M mostradas a nombre de quien no las
--    recibió, con $31.128 M de Integración Social rotulados «Cultura». Cuál
--    de los siete nombres ganaba dependía del ORDEN de las filas, así que el
--    corte siguiente podía renombrar al mismo tercero sin que nadie lo pida.
--
--    `bp_sap` entra en la llave. Va sobre `COALESCE(bp_sap, -1)` y no sobre
--    la columna pelada porque es nullable y dos NULL no chocan: un corte que
--    dejara de traer el business partner crearía una fila nueva por carga.
--    Las 1.412 filas actuales lo traen todas.
--
-- ADITIVO EN DATOS: no borra ni reescribe ninguna fila. Las 1.412 de
-- `tercero_sap` son únicas también bajo la llave de tres, así que el índice
-- nuevo entra sin conflicto. Los seis terceros que faltan del NIT distrital
-- aparecen solos en la próxima carga, cuando el upsert los inserte.
--
-- Rollback en `rollback_028_crp_llaves_naturales.sql`.

BEGIN;

-- ── 1. La PK natural del CRP, NOT NULL ─────────────────────────────────
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM crp
               WHERE n_interno_crp IS NULL OR n_posicion_crp IS NULL) THEN
        RAISE EXCEPTION
            'Hay filas de crp sin (n_interno_crp, n_posicion_crp). '
            'Resuélvelas antes: el NOT NULL las rechazaría.';
    END IF;
    IF (SELECT is_nullable FROM information_schema.columns
        WHERE table_name = 'crp' AND column_name = 'n_interno_crp') = 'YES' THEN
        EXECUTE 'ALTER TABLE crp ALTER COLUMN n_interno_crp SET NOT NULL';
    END IF;
    IF (SELECT is_nullable FROM information_schema.columns
        WHERE table_name = 'crp' AND column_name = 'n_posicion_crp') = 'YES' THEN
        EXECUTE 'ALTER TABLE crp ALTER COLUMN n_posicion_crp SET NOT NULL';
    END IF;
END $$;

-- ── 2. El tercero se identifica por documento Y business partner ────────
-- Es una CONSTRAINT, no un índice suelto: hay que soltarla por ahí. La nueva
-- no puede ser constraint porque va sobre una expresión (`COALESCE`), y eso
-- Postgres solo lo admite como índice único.
ALTER TABLE tercero_sap DROP CONSTRAINT IF EXISTS uq_tercero_sap_doc;
DROP INDEX IF EXISTS uq_tercero_sap_doc;

CREATE UNIQUE INDEX IF NOT EXISTS uq_tercero_sap_doc_bp
    ON tercero_sap (tipo_doc, num_doc, COALESCE(bp_sap, -1));

COMMENT ON COLUMN tercero_sap.bp_sap IS
    'Business partner de SAP. Entra en la llave junto con el documento: siete '
    'entidades distritales comparten el NIT de Bogota D.C. (899999061) y esto '
    'es lo unico que las separa.';

COMMIT;
