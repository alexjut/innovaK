-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║ 038 · Borrar un soporte deja de destruirlo                                ║
-- ╚══════════════════════════════════════════════════════════════════════════╝
--
-- ✅ APLICADO el 2026-10-15, encabezado corregido en el MISMO movimiento.
--    Respaldo del día: 9 h de antigüedad al aplicar.
--
-- ## El defecto (punto 3.3 del plan)
--
-- Hoy `DELETE /presupuesto/api/formulaciones/<id>/documentos/<doc_id>/` hace
-- esto:
--
--     with transaction.atomic():
--         RequisitoCumplido...update(estado='pendiente', documento=None)
--         d.delete()                  -- borra la fila
--     mongo_storage.borrar(mongo_id)  -- y destruye el contenido, FUERA de la
--                                     -- transacción
--
-- O sea: una sola petición destruye irreversiblemente un soporte de un
-- expediente contractual. No hay papelera, no hay retención, y el blob se borra
-- después de que la transacción ya cerró, así que ni siquiera un fallo posterior
-- lo puede devolver.
--
-- Queda rastro en la auditoría —`documento:baja` con el nombre— pero el
-- documento no vuelve. Y el nombre de un archivo no es el archivo: si lo que se
-- borró era el estudio previo que sustentaba un requisito crítico, lo que se
-- perdió es la prueba.
--
-- ## El arreglo
--
-- Baja lógica. La fila se queda, el blob se queda, y se anota quién lo quitó,
-- cuándo y por qué. El soporte deja de contar como evidencia y deja de
-- aparecer en el listado —eso no cambia—, pero se puede recuperar.
--
-- El requisito sigue volviendo a «pendiente», que ya estaba bien y por el
-- motivo que dice el propio código: «dejar el requisito en cumplido sin soporte
-- sería afirmar algo que ya no se puede probar».
--
-- ## Lo que este script NO resuelve
--
-- La RETENCIÓN. Un soporte guardado para siempre es una decisión de habeas data
-- que no es nuestra: es el punto 4.6 del plan («retención y datos personales de
-- los soportes de un expediente contractual»). Hasta que eso se decida, se
-- conserva, que es el lado reversible del error: un archivo que sobra se puede
-- purgar después; uno destruido no vuelve.
--
-- Rollback: rollback_038_formulacion_soporte_reversible.sql

BEGIN;

ALTER TABLE formulacion_documento
    ADD COLUMN IF NOT EXISTS eliminado_en      timestamptz,
    ADD COLUMN IF NOT EXISTS eliminado_por_id  bigint,
    ADD COLUMN IF NOT EXISTS eliminado_motivo  text;

COMMENT ON COLUMN formulacion_documento.eliminado_en IS
    'Baja lógica. Con valor, el soporte no cuenta como evidencia ni aparece en '
    'el listado, pero la fila y el blob en Mongo SIGUEN AHÍ. Antes del DDL 038 '
    'el borrado destruía los dos y no había vuelta.';

-- El listado y la evidencia filtran por esto, así que el índice es el que
-- sostiene la consulta normal.
CREATE INDEX IF NOT EXISTS idx_formulacion_doc_vivos
    ON formulacion_documento (formulacion_id)
 WHERE eliminado_en IS NULL;

-- Un soporte dado de baja tiene que decir QUIÉN y CUÁNDO. Sin eso la baja es
-- indistinguible de una fila corrupta.
ALTER TABLE formulacion_documento
    DROP CONSTRAINT IF EXISTS ck_formulacion_doc_baja;
ALTER TABLE formulacion_documento
    ADD CONSTRAINT ck_formulacion_doc_baja
    CHECK (eliminado_en IS NULL OR eliminado_por_id IS NOT NULL);

COMMIT;
