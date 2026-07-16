-- Persiste el RESULTADO de geocodificar la dirección de la organización.
--
-- Hasta ahora `estrato_ideca_org` guardaba el estrato pero no CÓMO se llegó a
-- él, ni por qué una fila quedaba en NULL. Y un NULL puede significar tres cosas
-- muy distintas:
--
--   * la organización no declaró dirección          → no sabemos nada
--   * la dirección no se pudo ubicar                → no sabemos dónde está
--   * la dirección resolvió FUERA de Kennedy        → sabemos que NO está acá
--
-- Las tres se veían igual (NULL) y son decisiones distintas. La tercera además
-- es una decisión de política: Alex, 2026-07-16 — esas organizaciones reciben
-- bono de estrato 0, porque el bono compensa operar en territorio vulnerable
-- DE KENNEDY, y ellas no operan acá.
--
-- Medido sobre el piloto (evento 62, 24 inscripciones): 7 declararon un barrio
-- de Kennedy y su dirección cae en otra localidad. Casi un tercio. Sin esta
-- columna, el puntaje no tiene cómo saberlo.
--
-- Aditivo y reversible: no toca datos existentes.
-- Rollback en 011_fuera_kennedy_geo_metodo_rollback.sql.

BEGIN;

ALTER TABLE inscripcion_banco_iniciativa
    ADD COLUMN IF NOT EXISTS fuera_kennedy BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS geo_metodo VARCHAR(20);

COMMENT ON COLUMN inscripcion_banco_iniciativa.fuera_kennedy IS
    'True si la dirección declarada resolvió FUERA del contorno de Kennedy '
    '(o si su vía no tiene ni una placa en la localidad). Decisión Alex '
    '2026-07-16: estas organizaciones reciben bono_estrato = 0 — el bono '
    'compensa operar en territorio vulnerable DE Kennedy. FALSE por defecto '
    'es seguro: sin geocodificar, estrato_ideca_org queda NULL y la regla R2 '
    'del bono ya devuelve 0.';

COMMENT ON COLUMN inscripcion_banco_iniciativa.geo_metodo IS
    'Cómo se resolvió (auditable, alimenta un puntaje): placa_exacta | '
    'via_mayoria | fuera_kennedy | sin_hit | no_parseable | sin_direccion | '
    'barrio (rescate por barrio declarado). NULL = nunca se geocodificó.';

-- Las 7 fuera de Kennedy son revisión manual: se consultan seguido.
CREATE INDEX IF NOT EXISTS idx_inscripcion_fuera_kennedy
    ON inscripcion_banco_iniciativa (fuera_kennedy) WHERE fuera_kennedy;

COMMIT;
