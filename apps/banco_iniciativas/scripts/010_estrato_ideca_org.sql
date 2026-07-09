-- ============================================================================
-- PR-4 — Estrato oficial (IDECA) de la ORGANIZACIÓN, aproximado por barrio.
--
-- NO reemplaza `inscripcion_banco_iniciativa.estrato` (1-4), que es lo que la
-- organización DECLARA. Este campo es el estrato OFICIAL del barrio que declaró,
-- y existe para la validación cruzada declarado-vs-oficial. NO alimenta puntaje.
--
-- Decisión de Javier (líder técnico), 2026-07-09: se aproxima por el barrio
-- declarado (mayoría de las manzanas del barrio), NO se geocodifica la dirección
-- (texto libre, sin lat/lng). El Comité solo necesita saber que es una
-- aproximación, no aprobar el método.
--
-- Aditivo y reversible: una columna nullable nueva. Rollback al final.
-- Requiere backup < 24 h y confirmación de Alex.
-- ============================================================================

ALTER TABLE inscripcion_banco_iniciativa
    ADD COLUMN IF NOT EXISTS estrato_ideca_org SMALLINT;

COMMENT ON COLUMN inscripcion_banco_iniciativa.estrato_ideca_org IS
    'Estrato oficial (IDECA) aproximado por el barrio declarado: mayoria de las '
    'manzanas del barrio, excluyendo las de estrato 0 (sin estrato oficial). '
    'Aproximacion, no el punto exacto de la sede. Para validacion cruzada contra '
    'la columna estrato (autodeclarado 1-4). NULL = no se pudo determinar '
    '(barrio sin geometria - deuda M22). No se infiere.';

-- ─────────────────────────────────────────────────────────────────────────
-- ROLLBACK
-- ─────────────────────────────────────────────────────────────────────────
-- ALTER TABLE inscripcion_banco_iniciativa DROP COLUMN IF EXISTS estrato_ideca_org;
