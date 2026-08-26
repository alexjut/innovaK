-- rollback_015_etapa_en_elaboracion.sql — quita la etapa «En elaboración».
--
-- OJO: falla a propósito si algún contrato la está usando. Borrar la fila
-- les BORRARÍA la etapa en silencio: la FK `contrato_etapa_codigo_fkey` es
-- ON DELETE SET NULL, no RESTRICT. O sea que un DELETE pelado NO falla —pasa
-- limpio y deja los contratos con `etapa_codigo` en NULL, indistinguibles de
-- los que nunca tuvieron etapa registrada. Esta comprobación es lo único que
-- lo impide; no es un mensaje más amable, es la guarda.
--
-- Para ver cuáles la usan antes de decidir:
--   SELECT id, contrato_tipo, contrato_numero FROM contrato WHERE etapa_codigo = 5;

BEGIN;

DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM contrato WHERE etapa_codigo = 5;
    IF n > 0 THEN
        RAISE EXCEPTION 'No se puede quitar «En elaboración»: % contrato(s) la usan. '
                        'Cambiales la etapa primero.', n;
    END IF;
END $$;

DELETE FROM etapa_contrato WHERE codigo = 5;

COMMIT;
