-- Rollback de 039. Borra la tabla de observaciones.
--
-- ⚠ DESTRUCTIVO Y NO RECUPERABLE. Se pierde el motivo por el que cada
-- formulación volvió atrás, que es precisamente lo que la tabla existe para
-- conservar. No hay otra copia: la auditoría guarda el cambio de ESTADO, no el
-- contenido de cada observación ni su respuesta.
--
-- Antes de correrlo, al menos mirar qué se va:
--     SELECT formulacion_id, estado, COUNT(*) FROM formulacion_observacion
--     GROUP BY 1, 2 ORDER BY 1;

BEGIN;

DROP TABLE IF EXISTS formulacion_observacion;

COMMIT;
