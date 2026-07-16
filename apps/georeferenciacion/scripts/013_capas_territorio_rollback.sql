-- Rollback de 013_capas_territorio.sql.
--
-- Seguro de correr: las dos tablas son copia de una fuente pública (Catastro) y
-- nada del sistema escribe en ellas — solo `sync_capa` las llena. No hay FK
-- apuntando aquí. Se pierden únicamente los datos sincronizados, que se
-- recuperan con:
--     python manage.py sync_capa sector_catastral
--     python manage.py sync_capa barrios_legalizados

BEGIN;

DROP TABLE IF EXISTS barrio_legalizado;
DROP TABLE IF EXISTS sector_catastral;

COMMIT;
