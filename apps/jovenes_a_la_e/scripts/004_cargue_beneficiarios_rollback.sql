-- Rollback de 004 — deja `entrega_beca` como estaba y borra el lote.
--
-- ⚠️ LEE ESTO ANTES DE CORRERLO
--
-- El rollback NO es simétrico, y no puede serlo: la llave vieja
-- `UNIQUE (evento_id, numero_documento)` es MÁS restrictiva que la nueva. Si
-- ya se cargó una persona con dos matrículas en la misma vigencia y el mismo
-- evento —el caso que este DDL vino a permitir—, restaurarla es imposible sin
-- borrar una de las dos filas. Por eso el script se detiene y lo dice, en vez
-- de fallar con un error de índice duplicado que no explica nada.
--
-- Borrar las columnas PIERDE datos: vigencia, códigos SNIES y la trazabilidad
-- del lote de cada fila cargada. Si hay entregas con `origen='CARGA'`, lo
-- razonable es borrarlas primero (o anular su lote) y decidir a conciencia,
-- no dejar que un DROP COLUMN lo resuelva por omisión.

BEGIN;

DO $$
DECLARE
    colisiones INTEGER;
    cargadas   INTEGER;
BEGIN
    SELECT count(*) INTO colisiones FROM (
        SELECT evento_id, numero_documento
          FROM entrega_beca
         GROUP BY evento_id, numero_documento
        HAVING count(*) > 1
    ) x;
    IF colisiones > 0 THEN
        RAISE EXCEPTION
            'Hay % combinaciones (evento, documento) repetidas: la llave vieja no se puede restaurar sin borrar filas. Resuélvelas a mano y vuelve a correr este rollback.',
            colisiones;
    END IF;

    SELECT count(*) INTO cargadas FROM entrega_beca WHERE origen = 'CARGA';
    IF cargadas > 0 THEN
        RAISE EXCEPTION
            'Hay % entregas con origen CARGA. Bórralas o anula su lote antes de revertir: el DROP COLUMN se llevaría su vigencia, sus códigos SNIES y su trazabilidad.',
            cargadas;
    END IF;
END $$;

-- El flag del tipo de evento vuelve a como estaba.
UPDATE tipo_evento SET requiere_actividad_plan = FALSE WHERE codigo = 'JOVENES_BECA';

ALTER TABLE entrega_beca DROP CONSTRAINT IF EXISTS fk_entrega_beca_cargue;

DROP INDEX IF EXISTS uq_cargue_hash_vigencia;
DROP INDEX IF EXISTS idx_cargue_evento;
DROP TABLE IF EXISTS cargue_beneficiarios;

DROP INDEX IF EXISTS uq_entrega_beca_matricula;
DROP INDEX IF EXISTS idx_entrega_beca_vigencia;
DROP INDEX IF EXISTS idx_entrega_beca_cargue;

CREATE UNIQUE INDEX IF NOT EXISTS uq_entrega_beca_evento_doc
    ON entrega_beca (evento_id, numero_documento);

ALTER TABLE entrega_beca DROP CONSTRAINT IF EXISTS ck_entrega_beca_vigencia;
ALTER TABLE entrega_beca DROP CONSTRAINT IF EXISTS ck_entrega_beca_origen;

ALTER TABLE entrega_beca
    DROP COLUMN IF EXISTS cargue_id,
    DROP COLUMN IF EXISTS snies_ies,
    DROP COLUMN IF EXISTS snies_programa,
    DROP COLUMN IF EXISTS origen,
    DROP COLUMN IF EXISTS vigencia;

COMMIT;
