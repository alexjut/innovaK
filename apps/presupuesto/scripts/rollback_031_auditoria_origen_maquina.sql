-- Reversión del 031. Devuelve `auditoria_dato` a su forma anterior.
--
-- OJO: restaurar el NOT NULL de `usuario_id` falla si ya existe alguna fila de
-- origen 'maquina'. Eso es deliberado — revertir no puede borrar registros de
-- auditoría en silencio. Si hay filas de máquina, hay que decidir primero qué
-- se hace con ellas y dejarlo escrito.

BEGIN;

DROP INDEX IF EXISTS idx_auditoria_origen_maquina;
ALTER TABLE auditoria_dato DROP CONSTRAINT IF EXISTS ck_auditoria_confianza;
ALTER TABLE auditoria_dato DROP CONSTRAINT IF EXISTS ck_auditoria_origen;

-- Se niega a seguir si hay auditoría de máquina que se perdería.
DO $$
DECLARE n bigint;
BEGIN
    SELECT COUNT(*) INTO n FROM auditoria_dato WHERE usuario_id IS NULL;
    IF n > 0 THEN
        RAISE EXCEPTION 'Hay % filas de auditoría sin usuario (origen máquina). '
                        'Revertir las dejaría fuera de la restricción NOT NULL. '
                        'Decidir qué se hace con ellas ANTES de revertir.', n;
    END IF;
END $$;

ALTER TABLE auditoria_dato ALTER COLUMN usuario_id SET NOT NULL;
ALTER TABLE auditoria_dato
    DROP COLUMN IF EXISTS entrada_hash,
    DROP COLUMN IF EXISTS confianza,
    DROP COLUMN IF EXISTS modelo_version,
    DROP COLUMN IF EXISTS modelo,
    DROP COLUMN IF EXISTS origen;

COMMIT;
