-- Rollback de 003_n27_limpieza_datos.sql
-- Restaurar desde backup `poblacion_kennedy_pre_n27_<timestamp>.dump`
-- es lo más seguro (este script reconstruye solo si los datos no han
-- cambiado mucho desde el cambio).

BEGIN;

-- Revertir typo Participación → Prticipación
UPDATE subgrupo
   SET nombre = 'Prticipación'
 WHERE id = 3 AND nombre = 'Participación';

-- Revertir username (los grupos NO se restauran automáticamente — usar dump)
UPDATE usuario
   SET username = 'Coordionador'
 WHERE id = 9 AND username = 'Coordinador';

-- Re-crear subgrupo id=5 Seguridad (los funcionarios y eventos NO se
-- revierten automáticamente — usar dump para restauración completa)
INSERT INTO subgrupo (id, nombre, dependencia_id)
VALUES (5, 'Seguridad', 3)
ON CONFLICT DO NOTHING;

COMMIT;
