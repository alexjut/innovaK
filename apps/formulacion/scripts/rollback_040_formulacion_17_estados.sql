-- Rollback de 040. Vuelve a los 10 estados genéricos.
--
-- ⚠ Antes de correrlo hay que MOVER las formulaciones que estén en un estado
-- que va a desaparecer (del 11 al 17), porque su FK quedaría apuntando a nada:
--
--     SELECT estado_codigo, COUNT(*) FROM formulacion
--      WHERE estado_codigo > 10 GROUP BY 1;
--
-- Y se pierde la clasificación: las compuertas de observaciones dependen de
-- `es_revision` y `es_observacion`, así que tras este rollback hay que volver a
-- anclarlas al nombre del estado.

BEGIN;

DELETE FROM formulacion_transicion;
DELETE FROM formulacion_estado WHERE codigo > 10;

UPDATE formulacion_estado SET
    nombre = v.nombre, orden = v.orden, es_final = v.es_final,
    bloquea_contratacion = v.bloquea
FROM (VALUES
    (1,'Borrador',1,false,true), (2,'En elaboración',2,false,true),
    (3,'En formulación',3,false,true), (4,'Pendiente de información',4,false,true),
    (5,'En revisión',5,false,true), (6,'Con observaciones',6,false,true),
    (7,'Subsanando',7,false,true), (8,'Aprobada',8,false,true),
    (9,'Lista para contratación',9,false,false), (10,'Cancelada',10,true,true)
) AS v(codigo, nombre, orden, es_final, bloquea)
WHERE formulacion_estado.codigo = v.codigo;

INSERT INTO formulacion_transicion (origen, destino) VALUES
    (1,2),(1,10),(2,3),(2,4),(2,10),(3,4),(3,5),(3,10),(4,3),(4,10),
    (5,6),(5,8),(5,10),(6,7),(6,10),(7,5),(7,10),(8,6),(8,9),(8,10),(9,6),(9,10);

DROP INDEX IF EXISTS idx_formulacion_estado_clase;
ALTER TABLE formulacion_estado
    DROP COLUMN IF EXISTS es_revision,
    DROP COLUMN IF EXISTS es_observacion,
    DROP COLUMN IF EXISTS carril;

COMMIT;
