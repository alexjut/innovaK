-- Rollback de 012_direccion_lonlat.sql.
--
-- OJO: esto SÍ borra dato propio, no una copia. Las coordenadas las captura el
-- ciudadano con el picker al inscribirse; no hay otra fuente que las tenga.
-- El backfill de las que ya existen se puede rehacer con:
--     python manage.py backfill_lonlat_banco --write
-- pero solo recupera las que el geocodificador logre resolver desde la dirección
-- en texto — NO el pin que la persona movió a mano.

BEGIN;

DROP INDEX IF EXISTS idx_inscripcion_banco_ubicada;

ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS inscripcion_banco_lonlat_bogota;

ALTER TABLE inscripcion_banco_iniciativa
    DROP COLUMN IF EXISTS direccion_lon,
    DROP COLUMN IF EXISTS direccion_lat;

COMMIT;
