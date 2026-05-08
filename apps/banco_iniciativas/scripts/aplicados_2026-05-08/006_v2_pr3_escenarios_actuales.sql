-- ============================================================================
-- 006_v2_pr3_escenarios_actuales.sql
-- Banco de Iniciativas v2 — PR-3: categoria_pot + tabla escenarios actuales
-- ============================================================================
-- Fecha:    2026-05-08
-- Autor:    Claude + Alex
-- Backup:   poblacion_kennedy_diario.dump 02:00 AM del día
-- Reversa:  bloque comentado al final del archivo
--
-- Cambios:
--   1. ALTER escenario: agrega columna categoria_pot VARCHAR(20) NULL
--      con CHECK en (red_estructurante, red_proximidad, otros_dotacionales).
--   2. UPDATE filas existentes para asignar categoría POT 2022.
--   3. INSERT 4 filas nuevas (Plazoleta, Humedal, Sendero, NTD).
--   4. CREATE TABLE inscripcion_banco_escenario_actual (puente M2M, BIGSERIAL,
--      UNIQUE (inscripcion_id, escenario_codigo), CASCADE en inscripcion).
--
-- Compatibilidad:
--   - escenario.categoria_pot es NULL para filas sin categorizar (Parque
--     genérico, propio, sin escenario, otro). El form los mostrará en un
--     bloque "Sin categoría POT" al final.
--   - Las inscripciones legacy NO tienen filas en
--     inscripcion_banco_escenario_actual (tabla nueva). Eso es semántico:
--     la sección no existía cuando ellas se enviaron.
-- ============================================================================

BEGIN;

-- ── 1. Categoría POT en catálogo escenario ─────────────────────────────────
ALTER TABLE escenario
  ADD COLUMN IF NOT EXISTS categoria_pot VARCHAR(20) NULL;

COMMENT ON COLUMN escenario.categoria_pot IS
  'Categoría POT 2022: red_estructurante (parques metropolitanos/zonales >1ha), '
  'red_proximidad (vecinales/de bolsillo <1ha), otros_dotacionales '
  '(salones comunales, plazoletas, humedales, senderos). NULL si no clasifica.';

-- 2. Categorización de las 13 filas existentes (POT 2022)
UPDATE escenario SET categoria_pot = 'red_estructurante' WHERE codigo = 3;   -- Polideportivo cubierto
UPDATE escenario SET categoria_pot = 'red_estructurante' WHERE codigo = 7;   -- Pista de atletismo
UPDATE escenario SET categoria_pot = 'red_estructurante' WHERE codigo = 8;   -- Patinódromo / ciclorruta
UPDATE escenario SET categoria_pot = 'red_estructurante' WHERE codigo = 9;   -- Piscina
UPDATE escenario SET categoria_pot = 'red_estructurante' WHERE codigo = 10;  -- Coliseo cubierto

UPDATE escenario SET categoria_pot = 'red_proximidad' WHERE codigo = 1;      -- Cancha fútbol/fut. sala
UPDATE escenario SET categoria_pot = 'red_proximidad' WHERE codigo = 2;      -- Cancha múltiple
UPDATE escenario SET categoria_pot = 'red_proximidad' WHERE codigo = 6;      -- Gimnasio o sala

UPDATE escenario SET categoria_pot = 'otros_dotacionales' WHERE codigo = 5;  -- Salón comunal / casa cultura

-- codigos 4 (Parque genérico), 11 (propio), 12 (sin escenario), 13 (otro)
-- quedan con categoria_pot = NULL → se muestran en bloque "sin categoría".

-- 3. INSERT filas nuevas (POT 2022)
-- OVERRIDING SYSTEM VALUE porque codigo es identity GENERATED ALWAYS.
INSERT INTO escenario (codigo, nombre, activo, orden, categoria_pot)
OVERRIDING SYSTEM VALUE VALUES
  (14, 'Plazoleta',                          true, 14, 'otros_dotacionales'),
  (15, 'Humedal',                            true, 15, 'otros_dotacionales'),
  (16, 'Sendero o zona verde',               true, 16, 'otros_dotacionales'),
  (17, 'Escenario NTD (No Tradicional Deportivo)', true, 17, 'red_proximidad')
ON CONFLICT (codigo) DO UPDATE SET
  nombre        = EXCLUDED.nombre,
  activo        = EXCLUDED.activo,
  orden         = EXCLUDED.orden,
  categoria_pot = EXCLUDED.categoria_pot;

-- Avanzar la secuencia identity al máximo usado (defensivo).
SELECT setval(
  pg_get_serial_sequence('escenario', 'codigo'),
  GREATEST(17, (SELECT COALESCE(MAX(codigo), 0) FROM escenario))
);

-- CHECK constraint para integridad (idempotente con DO/IF NOT EXISTS).
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'escenario_categoria_pot_check'
  ) THEN
    ALTER TABLE escenario
      ADD CONSTRAINT escenario_categoria_pot_check
      CHECK (categoria_pot IS NULL OR categoria_pot IN
             ('red_estructurante', 'red_proximidad', 'otros_dotacionales'));
  END IF;
END$$;

-- ── 4. Tabla puente: escenarios uso actual ─────────────────────────────────
CREATE TABLE IF NOT EXISTS inscripcion_banco_escenario_actual (
  id               BIGSERIAL PRIMARY KEY,
  inscripcion_id   BIGINT   NOT NULL REFERENCES inscripcion_banco_iniciativa(id)
                                       ON DELETE CASCADE,
  escenario_codigo SMALLINT NOT NULL REFERENCES escenario(codigo)
                                       ON DELETE RESTRICT,
  CONSTRAINT uq_insc_banco_esc_actual UNIQUE (inscripcion_id, escenario_codigo)
);

CREATE INDEX IF NOT EXISTS idx_insc_banco_esc_actual_insc
  ON inscripcion_banco_escenario_actual(inscripcion_id);

CREATE INDEX IF NOT EXISTS idx_insc_banco_esc_actual_esc
  ON inscripcion_banco_escenario_actual(escenario_codigo);

COMMENT ON TABLE inscripcion_banco_escenario_actual IS
  'M2M: escenarios donde la organización desarrolla actividades '
  'actualmente (Sección 3 nueva). Distinto de inscripcion_banco_escenario '
  'que captura "escenarios requeridos para la propuesta" (Sección 7).';

COMMIT;

-- ============================================================================
-- VERIFICACIÓN MANUAL POSTERIOR (correr después de aplicar)
-- ============================================================================
-- SELECT codigo, nombre, categoria_pot FROM escenario ORDER BY orden, codigo;
-- \d+ inscripcion_banco_escenario_actual

-- ============================================================================
-- SCRIPT DE REVERSA (en caso de necesitar rollback manual)
-- ============================================================================
-- BEGIN;
-- DROP TABLE IF EXISTS inscripcion_banco_escenario_actual;
-- DELETE FROM escenario WHERE codigo IN (14, 15, 16, 17);
-- ALTER TABLE escenario DROP CONSTRAINT IF EXISTS escenario_categoria_pot_check;
-- ALTER TABLE escenario DROP COLUMN IF EXISTS categoria_pot;
-- COMMIT;
