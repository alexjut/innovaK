-- =============================================================================
-- N20: trazabilidad organizacional en wizards de caracterización
-- =============================================================================
-- Agrega columna `funcionario_id INTEGER` (nullable, FK a funcionario.id
-- con ON DELETE SET NULL) en las 6 tablas `caracterizacion_*`.
--
-- Motivación:
-- Cuando un funcionario llena `/dashboard/caracterizacion/<sector>/` SIN
-- evento, la fila queda con `evento_id = NULL` y no se sabe quién la
-- levantó. Con `funcionario_id` se puede auditar quién recolectó cada
-- caracterización y desde qué subgrupo (vía funcionario.subgrupo_id).
--
-- Nullable porque:
--   1. Las filas históricas (pre-N20) no tienen funcionario asignado.
--   2. Los wizards públicos (acceso por QR sin login) no tienen funcionario.
--
-- ON DELETE SET NULL para no perder caracterizaciones si se desactiva el
-- funcionario (la fila histórica queda huérfana pero válida).
--
-- Aplicado: 2026-05-11
-- Backup pre-cambio: poblacion_kennedy_pre_n20_<timestamp>.dump
-- Rollback: 002_n20_funcionario_id_rollback.sql
-- =============================================================================

BEGIN;

ALTER TABLE caracterizacion_cultura
  ADD COLUMN IF NOT EXISTS funcionario_id INTEGER
  REFERENCES funcionario(id) ON DELETE SET NULL;

ALTER TABLE caracterizacion_deporte
  ADD COLUMN IF NOT EXISTS funcionario_id INTEGER
  REFERENCES funcionario(id) ON DELETE SET NULL;

ALTER TABLE caracterizacion_mujer
  ADD COLUMN IF NOT EXISTS funcionario_id INTEGER
  REFERENCES funcionario(id) ON DELETE SET NULL;

ALTER TABLE caracterizacion_salud
  ADD COLUMN IF NOT EXISTS funcionario_id INTEGER
  REFERENCES funcionario(id) ON DELETE SET NULL;

ALTER TABLE caracterizacion_poblacional
  ADD COLUMN IF NOT EXISTS funcionario_id INTEGER
  REFERENCES funcionario(id) ON DELETE SET NULL;

ALTER TABLE caracterizacion_participacion_ciudadana
  ADD COLUMN IF NOT EXISTS funcionario_id INTEGER
  REFERENCES funcionario(id) ON DELETE SET NULL;

-- Índices para consultas tipo "todas las caracterizaciones que levantó X".
CREATE INDEX IF NOT EXISTS idx_caract_cultura_funcionario
  ON caracterizacion_cultura(funcionario_id);
CREATE INDEX IF NOT EXISTS idx_caract_deporte_funcionario
  ON caracterizacion_deporte(funcionario_id);
CREATE INDEX IF NOT EXISTS idx_caract_mujer_funcionario
  ON caracterizacion_mujer(funcionario_id);
CREATE INDEX IF NOT EXISTS idx_caract_salud_funcionario
  ON caracterizacion_salud(funcionario_id);
CREATE INDEX IF NOT EXISTS idx_caract_poblacional_funcionario
  ON caracterizacion_poblacional(funcionario_id);
CREATE INDEX IF NOT EXISTS idx_caract_participacion_funcionario
  ON caracterizacion_participacion_ciudadana(funcionario_id);

COMMIT;
