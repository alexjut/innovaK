-- Rollback de 037. Quita el índice y la columna.
--
-- ⚠ DEJA EL FLUJO SIN GUARDA DE ROL. La función `cambiar_estado` niega por
-- defecto cuando no encuentra el carril, así que tras este rollback NINGUNA
-- transición se podrá ejecutar salvo por un superusuario. Es el fallo seguro y
-- es deliberado: volver a un estado donde cualquiera aprueba su propia
-- formulación sería peor que trancar el flujo.

BEGIN;

DROP INDEX IF EXISTS idx_formulacion_transicion_rol;

ALTER TABLE formulacion_transicion
    DROP COLUMN IF EXISTS rol_requerido;

COMMIT;
