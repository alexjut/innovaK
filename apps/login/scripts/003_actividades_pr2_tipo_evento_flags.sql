-- ============================================================================
-- PR-2 actividades — Enriquecer tipo_evento + GENERICO + endurecer Banco
-- Sesión 2026-05-06. Backup pre-aplicación: poblacion_kennedy_diario.dump
-- (02:00, ~1.9 MB).
--
-- Idempotente: usa IF NOT EXISTS / ON CONFLICT.
-- Reversible: DROP COLUMN al final del archivo (comentado).
-- ============================================================================

BEGIN;

-- 1. Columnas nuevas en tipo_evento --------------------------------------------
ALTER TABLE tipo_evento
  ADD COLUMN IF NOT EXISTS icono                   VARCHAR(50),
  ADD COLUMN IF NOT EXISTS color                   VARCHAR(7),
  ADD COLUMN IF NOT EXISTS orden                   SMALLINT,
  ADD COLUMN IF NOT EXISTS permite_inscripcion     BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS permite_caracterizacion BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS permite_qr              BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS requiere_actividad_plan BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Índice de navegación por tipo (la nueva UI lo usa para Pantalla 2) -------
CREATE INDEX IF NOT EXISTS idx_evento_tipo_codigo
  ON evento (tipo_evento_codigo)
  WHERE tipo_evento_codigo IS NOT NULL;

-- 3. Backfill de tipos existentes (los 6 vivos) -------------------------------
UPDATE tipo_evento SET
    icono = 'fa-trophy',
    color = '#3B82F6',
    orden = 10,
    permite_inscripcion = TRUE,
    permite_qr = TRUE
  WHERE codigo = 'BANCO_INICIATIVAS';

UPDATE tipo_evento SET
    icono = 'fa-clipboard-list',
    color = '#8B5CF6',
    orden = 20,
    permite_caracterizacion = TRUE,
    permite_qr = TRUE
  WHERE codigo = 'CARACTERIZACION';

UPDATE tipo_evento SET
    icono = 'fa-chalkboard-teacher',
    color = '#06B6D4',
    orden = 30,
    permite_qr = TRUE,
    requiere_actividad_plan = TRUE
  WHERE codigo = 'CAPACITACION';

UPDATE tipo_evento SET
    icono = 'fa-graduation-cap',
    color = '#10B981',
    orden = 40,
    permite_qr = TRUE,
    requiere_actividad_plan = TRUE
  WHERE codigo = 'CURSO';

UPDATE tipo_evento SET
    icono = 'fa-box-open',
    color = '#F59E0B',
    orden = 50,
    requiere_actividad_plan = TRUE
  WHERE codigo = 'ENTREGA';

UPDATE tipo_evento SET
    icono = 'fa-map-marker-alt',
    color = '#EF4444',
    orden = 60,
    permite_qr = TRUE
  WHERE codigo = 'INFO_TERRENO';

-- 4. Tipo GENERICO (catch-all para eventos sin tipo) --------------------------
INSERT INTO tipo_evento (
    codigo, nombre, descripcion, activo,
    icono, color, orden,
    permite_inscripcion, permite_caracterizacion, permite_qr, requiere_actividad_plan
) VALUES (
    'GENERICO',
    'Genérico',
    'Actividad sin tipo específico (eventos legacy o sin clasificación todavía).',
    TRUE,
    'fa-calendar-day',
    '#6B7280',
    99,
    FALSE, FALSE, FALSE, FALSE
)
ON CONFLICT (codigo) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion,
    activo = EXCLUDED.activo,
    icono = EXCLUDED.icono,
    color = EXCLUDED.color,
    orden = EXCLUDED.orden;

-- 5. Backfill: eventos con tipo_evento_codigo NULL → GENERICO -----------------
-- Reporta cuántos se actualizan.
UPDATE evento SET tipo_evento_codigo = 'GENERICO'
  WHERE tipo_evento_codigo IS NULL;

COMMIT;

-- ============================================================================
-- ROLLBACK (si fuera necesario):
-- ============================================================================
-- BEGIN;
-- ALTER TABLE tipo_evento
--   DROP COLUMN IF EXISTS icono,
--   DROP COLUMN IF EXISTS color,
--   DROP COLUMN IF EXISTS orden,
--   DROP COLUMN IF EXISTS permite_inscripcion,
--   DROP COLUMN IF EXISTS permite_caracterizacion,
--   DROP COLUMN IF EXISTS permite_qr,
--   DROP COLUMN IF EXISTS requiere_actividad_plan;
-- DROP INDEX IF EXISTS idx_evento_tipo_codigo;
-- UPDATE evento SET tipo_evento_codigo = NULL WHERE tipo_evento_codigo = 'GENERICO';
-- DELETE FROM tipo_evento WHERE codigo = 'GENERICO' AND NOT EXISTS (
--     SELECT 1 FROM evento WHERE tipo_evento_codigo = 'GENERICO'
-- );
-- COMMIT;
