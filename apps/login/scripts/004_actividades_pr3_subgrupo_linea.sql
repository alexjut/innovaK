-- ============================================================================
-- PR-3 actividades — Granularidad fina por subgrupo (subgrupo_linea)
-- Sesión 2026-05-06. Backup: poblacion_kennedy_diario.dump (02:00).
--
-- Crea tabla `subgrupo_linea` (líneas internas de cada área misional) +
-- agrega `evento.linea_id` para que cada actividad pueda asociarse a
-- una línea fina (Fútbol, Danza, Prevención, etc.) sin romper eventos
-- existentes (linea_id es nullable).
--
-- Crea 2 subgrupos nuevos en Inversión Local: Salud y Juventud, y
-- siembra 19 líneas iniciales repartidas en 5 áreas.
--
-- Idempotente: usa IF NOT EXISTS / ON CONFLICT / WHERE NOT EXISTS.
-- Reversible: ROLLBACK comentado al final.
-- ============================================================================

BEGIN;

-- 1. Subgrupos faltantes en Inversión Local (dep_id=3) ------------------------
INSERT INTO subgrupo (nombre, dependencia_id)
  SELECT 'Salud', 3
  WHERE NOT EXISTS (
    SELECT 1 FROM subgrupo WHERE nombre = 'Salud' AND dependencia_id = 3
  );

INSERT INTO subgrupo (nombre, dependencia_id)
  SELECT 'Juventud', 3
  WHERE NOT EXISTS (
    SELECT 1 FROM subgrupo WHERE nombre = 'Juventud' AND dependencia_id = 3
  );

-- 2. Tabla subgrupo_linea -----------------------------------------------------
CREATE TABLE IF NOT EXISTS subgrupo_linea (
    id           BIGSERIAL PRIMARY KEY,
    subgrupo_id  INTEGER NOT NULL REFERENCES subgrupo(id) ON DELETE CASCADE,
    codigo       VARCHAR(50) NOT NULL,
    nombre       VARCHAR(150) NOT NULL,
    descripcion  TEXT,
    activo       BOOLEAN NOT NULL DEFAULT TRUE,
    orden        SMALLINT,
    created_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    UNIQUE (subgrupo_id, codigo)
);

CREATE INDEX IF NOT EXISTS idx_subgrupo_linea_subgrupo
  ON subgrupo_linea (subgrupo_id);
CREATE INDEX IF NOT EXISTS idx_subgrupo_linea_activo
  ON subgrupo_linea (activo)
  WHERE activo = TRUE;

-- 3. evento.linea_id (nullable, no rompe eventos existentes) ------------------
ALTER TABLE evento
  ADD COLUMN IF NOT EXISTS linea_id BIGINT NULL REFERENCES subgrupo_linea(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_evento_linea_id
  ON evento (linea_id)
  WHERE linea_id IS NOT NULL;

-- 4. Seed de líneas iniciales (5 áreas, 19 líneas) ----------------------------
-- Resolución de subgrupo_id por nombre + dep_id=3 para evitar IDs hardcoded.
INSERT INTO subgrupo_linea (subgrupo_id, codigo, nombre, orden)
SELECT s.id, v.codigo, v.nombre, v.orden
FROM (VALUES
    -- Cultura (id=1)
    ('Cultura',  'DANZA',           'Danza',           10),
    ('Cultura',  'MUSICA',          'Música',          20),
    ('Cultura',  'ARTES_PLASTICAS', 'Artes plásticas', 30),
    ('Cultura',  'TEATRO',          'Teatro',          40),

    -- Deporte (id=2)
    ('Deporte',  'FUTBOL',          'Fútbol / Futsal', 10),
    ('Deporte',  'VOLEIBOL',        'Voleibol',        20),
    ('Deporte',  'ARTES_MARCIALES', 'Artes marciales', 30),
    ('Deporte',  'RECREODEPORTE',   'Recreodeporte',   40),

    -- Mujer (id=40)
    ('Mujer',    'FORMACION',       'Formación',       10),
    ('Mujer',    'EMPRENDIMIENTO',  'Emprendimiento',  20),
    ('Mujer',    'ACOMPANAMIENTO',  'Acompañamiento',  30),

    -- Salud (recién creado)
    ('Salud',    'PROMOCION',           'Promoción',           10),
    ('Salud',    'PREVENCION',          'Prevención',          20),
    ('Salud',    'ATENCION_COMUNITARIA','Atención comunitaria',30),
    ('Salud',    'ORIENTACION',         'Orientación',         40),

    -- Juventud (recién creado)
    ('Juventud', 'PARTICIPACION',           'Participación',           10),
    ('Juventud', 'FORMACION',               'Formación',               20),
    ('Juventud', 'EMPRENDIMIENTO',          'Emprendimiento',          30),
    ('Juventud', 'ACTIVIDADES_TERRITORIALES','Actividades territoriales',40)
) AS v (subgrupo_nombre, codigo, nombre, orden)
JOIN subgrupo s ON s.nombre = v.subgrupo_nombre AND s.dependencia_id = 3
ON CONFLICT (subgrupo_id, codigo) DO NOTHING;

COMMIT;

-- ============================================================================
-- ROLLBACK (si fuera necesario):
-- ============================================================================
-- BEGIN;
-- ALTER TABLE evento DROP COLUMN IF EXISTS linea_id;
-- DROP INDEX IF EXISTS idx_evento_linea_id;
-- DROP TABLE IF EXISTS subgrupo_linea CASCADE;
-- DELETE FROM subgrupo
--   WHERE nombre IN ('Salud', 'Juventud') AND dependencia_id = 3
--   AND NOT EXISTS (SELECT 1 FROM evento WHERE evento.subgrupo_id = subgrupo.id);
-- COMMIT;
