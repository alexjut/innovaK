-- =====================================================================
-- Cursos: CUPO máximo + LISTA DE ESPERA (absorción KDApp, PR-1).
-- Reusa la tabla de inscritos (participante_evento): un estado por inscripción
-- en vez de tabla nueva. Aplicar tras backup < 24 h. REVERSA al final.
-- =====================================================================
BEGIN;

-- Cupo máximo del curso/actividad (NULL = sin límite).
ALTER TABLE evento ADD COLUMN IF NOT EXISTS cupo_maximo INTEGER;

-- Estado de la inscripción: inscrito | espera | rechazado.
ALTER TABLE participante_evento
  ADD COLUMN IF NOT EXISTS estado VARCHAR(12) NOT NULL DEFAULT 'inscrito';

CREATE INDEX IF NOT EXISTS idx_part_evento_estado
  ON participante_evento(evento_id, estado);

COMMIT;

-- REVERSA:
--   ALTER TABLE evento DROP COLUMN IF EXISTS cupo_maximo;
--   ALTER TABLE participante_evento DROP COLUMN IF EXISTS estado;
-- =====================================================================
