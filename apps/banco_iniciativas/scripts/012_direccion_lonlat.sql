-- Coordenadas de la sede de la organización en la inscripción del Banco.
--
-- POR QUÉ:
--   Las 24 inscripciones del piloto (evento 62) NO se ven en el mapa, y la razón
--   es que no hay dónde mirarlas: la tabla nunca tuvo lat/lon. La dirección se
--   guarda como texto y la coordenada se resuelve aparte, en el caché del
--   geocodificador, que no está atado a la inscripción.
--
--   Peor: el formulario público YA usa el picker de direcciones (autocompletar
--   contra Catastro + pin en el mapa), que resuelve lon/lat y los deja en el
--   modelo del front... y `buildFormData()` los descarta al enviar. Se hace todo
--   el trabajo de ubicar la sede y se bota el resultado.
--
--   Esto viola la regla del proyecto: una dirección no es texto libre, se captura
--   contra Catastro y SE GUARDA con su lat/lon.
--
-- QUÉ NO RESUELVE:
--   El estrato NO sale de acá — lo da el geocodificador contra la placa
--   domiciliaria (`estrato_ideca_org`, ya existente). Estas columnas son para
--   UBICAR en el mapa, no para calificar.
--
-- ALCANCE:
--   Solo la sede (`direccion`). `direccion_espacio_ejecucion` queda para después:
--   hoy nadie la pinta y agregar columnas que nadie lee es deuda, no adelanto.
--
-- Nullable a propósito: de las 24 del piloto, 2 no declararon dirección y 7 están
-- fuera de Kennedy. NULL es la respuesta honesta para las que no se pueden ubicar;
-- inventarles un punto sería peor que no dibujarlas.
--
-- Aplicar con backup < 24 h. Rollback en 012_direccion_lonlat_rollback.sql.

BEGIN;

ALTER TABLE inscripcion_banco_iniciativa
    ADD COLUMN IF NOT EXISTS direccion_lon DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS direccion_lat DOUBLE PRECISION;

-- Bogotá, con margen. Ataja el error clásico de mandar (lat, lon) invertidos:
-- una sede en (4.6, -74.1) cae en el Índico y el mapa la dibuja en el mar.
ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS inscripcion_banco_lonlat_bogota;
ALTER TABLE inscripcion_banco_iniciativa
    ADD CONSTRAINT inscripcion_banco_lonlat_bogota CHECK (
        (direccion_lon IS NULL AND direccion_lat IS NULL)
        OR (direccion_lon BETWEEN -74.6 AND -73.9
            AND direccion_lat BETWEEN 3.7 AND 4.9)
    );

-- El mapa pide "las que tienen punto". Parcial: hoy 14 de 24 lo tendrán.
CREATE INDEX IF NOT EXISTS idx_inscripcion_banco_ubicada
    ON inscripcion_banco_iniciativa (direccion_lat, direccion_lon)
    WHERE direccion_lat IS NOT NULL;

COMMENT ON COLUMN inscripcion_banco_iniciativa.direccion_lon IS
    'Longitud WGS84 de la sede, resuelta por el picker de direcciones al capturar '
    '(Catastro + pin). NULL = no se pudo ubicar: sin dirección declarada o fuera '
    'de la cobertura. No inventar.';
COMMENT ON COLUMN inscripcion_banco_iniciativa.direccion_lat IS
    'Latitud WGS84 de la sede. Ver direccion_lon.';

COMMIT;
