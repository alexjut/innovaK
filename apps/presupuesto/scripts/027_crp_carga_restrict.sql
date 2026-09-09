-- ═══════════════════════════════════════════════════════════════════════
-- DDL 027 — `crp.carga_id` deja de borrar en cascada
--
-- LO QUE ESTABA MAL. El 026 puso `ON DELETE CASCADE` creyendo que `carga_id`
-- significaba «la carga que trajo esta fila». No: el upsert hace
-- `carga_id = EXCLUDED.carga_id` en cada corte, así que significa **la última
-- carga que la tocó**. Con CASCADE, borrar la carga más reciente —el gesto
-- natural para deshacer un corte mal subido— se lleva TODAS las filas de
-- `crp`, incluidas las que venían del primer corte.
--
-- Reproducido en transacción revertida: dos cargas, las mismas filas
-- upserteadas, `carga_id` apuntando todo a la segunda; `DELETE FROM crp_carga
-- WHERE id = <la segunda>` deja `crp` en CERO y el historial diciendo «2.630
-- filas, $226.745 M».
--
-- Y contradice la regla del módulo: «lo que desaparece se marca
-- `vigente=FALSE`, nunca se borra». La rompía la propia FK.
--
-- RESTRICT y no SET NULL: una fila de CRP sin carga no se puede fechar, y una
-- fila de plata que no se sabe de qué corte es no sirve para nada. Que el
-- DELETE falle obliga a decidir qué hacer con las filas antes de tirar la
-- carga, que es exactamente la conversación que hay que tener.
-- ═══════════════════════════════════════════════════════════════════════

BEGIN;

ALTER TABLE crp DROP CONSTRAINT IF EXISTS crp_carga_id_fkey;
ALTER TABLE crp
    ADD CONSTRAINT crp_carga_id_fkey
    FOREIGN KEY (carga_id) REFERENCES crp_carga(id) ON DELETE RESTRICT;

COMMIT;
