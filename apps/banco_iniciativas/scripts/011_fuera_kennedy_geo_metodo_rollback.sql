-- Rollback de 011_fuera_kennedy_geo_metodo.sql
--
-- Seguro de correr: las dos columnas son DERIVADAS. Se recalculan enteras con
-- `manage.py asignar_estrato_org --por-direccion --evento 62 --write`. El dato
-- original (la dirección que declaró la organización) no se toca.
--
-- OJO: si el bono de estrato ya está activo, borrar `fuera_kennedy` hace que
-- las organizaciones de fuera de Kennedy vuelvan a puntuar como si estuvieran
-- adentro. Desactivá el bono antes (tabla_estrato vacía en la rúbrica).

BEGIN;

DROP INDEX IF EXISTS idx_inscripcion_fuera_kennedy;

ALTER TABLE inscripcion_banco_iniciativa
    DROP COLUMN IF EXISTS geo_metodo,
    DROP COLUMN IF EXISTS fuera_kennedy;

COMMIT;
