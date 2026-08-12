-- Rollback de 003 — devuelve los marcadores al formato suelto.
--
-- Solo tiene sentido si hay que volver al código anterior. Ojo: al volver,
-- vuelve también la colisión por prefijo que motivó el cambio.

BEGIN;

-- '[infra_contrato=102] unidades terminadas (…)' → 'infra_contrato=102; unidades terminadas (…)'
UPDATE presu_avance_ind_periodo
   SET observaciones = 'infra_contrato=' || split_part(split_part(observaciones, '[infra_contrato=', 2), ']', 1)
                       || '; ' || btrim(split_part(observaciones, '] ', 2)),
       updated_at    = now()
 WHERE observaciones LIKE '[infra_contrato=%';

-- '[festival=4][acto=89]' → 'festival=4;acto=89'
UPDATE presu_avance_ind_periodo
   SET observaciones = 'festival=' || split_part(split_part(observaciones, '[festival=', 2), ']', 1)
                       || ';acto=' || split_part(split_part(observaciones, '[acto=', 2), ']', 1),
       updated_at    = now()
 WHERE observaciones LIKE '[festival=%';

COMMIT;
