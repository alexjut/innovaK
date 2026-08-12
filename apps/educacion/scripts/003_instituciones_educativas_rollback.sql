-- Rollback de 003 — borra el catálogo de instituciones y programas.
--
-- Es destructivo y no reversible: se pierden las COORDENADAS y las
-- correcciones de nombre que el área haya hecho a mano, que es justo el
-- trabajo que no está en ninguna otra parte. Los códigos se pueden volver a
-- generar desde `entrega_beca` corriendo la sincronización; la ubicación, no.
--
-- Por eso el script cuenta primero lo que se perdería y lo dice.

BEGIN;

DO $$
DECLARE ubicadas INTEGER; manuales INTEGER;
BEGIN
    SELECT count(*) INTO ubicadas FROM institucion_educativa WHERE latitud IS NOT NULL;
    SELECT count(*) INTO manuales FROM institucion_educativa WHERE origen = 'MANUAL';
    IF ubicadas > 0 OR manuales > 0 THEN
        RAISE WARNING 'Se van a perder % instituciones ubicadas y % creadas a mano. '
                      'Expórtalas antes si las necesitas: no se regeneran desde el cargue.',
                      ubicadas, manuales;
    END IF;
END $$;

DROP TABLE IF EXISTS programa_academico;      -- primero: depende de la otra
DROP TABLE IF EXISTS institucion_educativa;

COMMIT;
