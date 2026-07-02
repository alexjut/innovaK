-- ============================================================================
-- Banco de Iniciativas #62 — NC-01: detalle de escenarios (opera + solicita)
-- Fecha: 2026-07-02 · Rama: feat/banco-obs-nc
--
-- QA NC-01: la sección "escenarios que solicita tu proyecto" (y la de "opera")
-- debe capturar, por escenario, nombre/dirección/actividad. Decisión Alex:
-- REUSAR las escuelas de deporte del mapa (tabla `escuela`, 155 activas, ya con
-- nombre + dirección + coordenadas + UPZ) mediante un selector buscable; y si el
-- escenario NO está en la lista, permitir agregarlo a mano (nombre/dirección).
--
-- 100% aditivo: una tabla puente nueva. NO toca las 24 inscripciones ni la
-- tabla `escuela`. Atómico, idempotente, con ROLLBACK. Las "otras" que agregue
-- el ciudadano NO se insertan en `escuela` (evita ensuciar el catálogo del mapa
-- con datos sin validar); quedan como texto en esta tabla.
-- NO LO CORRE CLAUDE: lo revisa/corre Alex tras snapshot.
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS inscripcion_banco_escenario_detalle (
    id              BIGSERIAL PRIMARY KEY,
    inscripcion_id  BIGINT      NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    tipo            VARCHAR(10) NOT NULL CHECK (tipo IN ('opera', 'solicita')),
    -- Del mapa: referencia a la escuela de deporte (nombre/dirección/geo salen de ahí).
    escuela_id      INTEGER     NULL REFERENCES escuela(id),
    -- "Otra / no está en la lista": texto a mano.
    nombre          VARCHAR(120) NULL,
    direccion       VARCHAR(120) NULL,
    -- Actividad que realiza/realizaría en ese escenario (aplica a ambos casos).
    actividad       VARCHAR(120) NULL,
    created_at      TIMESTAMP   NOT NULL DEFAULT now(),
    -- Debe venir del mapa (escuela_id) O ser una "otra" con nombre.
    CONSTRAINT ibed_origen_chk CHECK (escuela_id IS NOT NULL OR nombre IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_ibed_inscripcion ON inscripcion_banco_escenario_detalle(inscripcion_id);
CREATE INDEX IF NOT EXISTS idx_ibed_escuela     ON inscripcion_banco_escenario_detalle(escuela_id);

COMMIT;

-- ============================================================================
-- ROLLBACK (tabla nueva/vacía; no toca nada existente).
-- ============================================================================
-- DROP TABLE IF EXISTS inscripcion_banco_escenario_detalle;
