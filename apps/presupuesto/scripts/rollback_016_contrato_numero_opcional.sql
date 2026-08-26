-- rollback_016_contrato_numero_opcional.sql — el número vuelve a ser obligatorio.
--
-- Sólo se puede si NINGÚN contrato lo tiene en NULL. Se comprueba primero y se
-- dice cuáles son, en vez de fallar con un error de restricción que obliga a
-- ir a buscarlos a mano.

BEGIN;

DO $$
DECLARE n integer; ids text;
BEGIN
    SELECT count(*), string_agg(id::text, ', ')
      INTO n, ids
      FROM contrato WHERE contrato_numero IS NULL;
    IF n > 0 THEN
        RAISE EXCEPTION 'No se puede volver a NOT NULL: % contrato(s) sin número (ids: %). '
                        'Asignales número o borralos primero.', n, ids;
    END IF;
END $$;

ALTER TABLE contrato ALTER COLUMN contrato_numero SET NOT NULL;

COMMIT;
