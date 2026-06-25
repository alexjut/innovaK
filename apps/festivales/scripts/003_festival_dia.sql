-- =====================================================================
-- Módulo Festivales — DDL-A (PR-A · Programación multi-día)
-- Festival → Día (festival_dia) → Actos (evento.festival_dia_id).
-- Cada día tiene metadata propia (tema, escenario, responsable).
--
-- Decisiones Alex 2026-06-25:
--   · entidad 'Día' con metadata propia (no agrupar por fecha en UI).
--   · responsable_id en la cabecera (festival) + responsable por día.
--   · limpieza: borrar el festival de prueba QA + formalizar FK subgrupo_id.
--
-- APLICAR tras backup < 24 h (~/Proyectos/postgres/backup_postgres.sh).
-- El contenedor innova_k NO tiene psql: aplicar con
--   connection.cursor().execute(open('.../003_festival_dia.sql').read())
-- REVERSA al final del archivo.
-- =====================================================================
BEGIN;

-- ── Limpieza previa: festival de prueba QA (tipo/subgrupo NULL) ───────
-- Sin actos asociados (0 eventos con festival_id). Se borra antes de
-- formalizar la FK de subgrupo_id.
DELETE FROM festival WHERE nombre = 'Festival de Prueba QA';

-- ── Día del festival (capa entre festival y sus actos) ───────────────
CREATE TABLE IF NOT EXISTS festival_dia (
    id BIGSERIAL PRIMARY KEY,
    festival_id BIGINT NOT NULL REFERENCES festival(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    nombre TEXT,                 -- tema/título del día (ej. "Día de apertura")
    escenario_texto TEXT,        -- escenario/lugar del día (parque, plaza…)
    responsable_id INTEGER REFERENCES funcionario(id) ON DELETE SET NULL,
    orden SMALLINT,              -- orden manual si dos días comparten fecha
    descripcion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_festival_dia UNIQUE (festival_id, fecha)
);
CREATE INDEX IF NOT EXISTS idx_festival_dia_festival ON festival_dia(festival_id);
CREATE INDEX IF NOT EXISTS idx_festival_dia_resp     ON festival_dia(responsable_id);

-- ── Liga cada acto (Evento) a su día ─────────────────────────────────
-- 🚨 toca la tabla central `evento` (una sola columna nullable).
ALTER TABLE evento ADD COLUMN IF NOT EXISTS festival_dia_id BIGINT
  REFERENCES festival_dia(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_evento_festival_dia ON evento(festival_dia_id);

-- ── Responsable general del festival (cabecera) ──────────────────────
ALTER TABLE festival ADD COLUMN IF NOT EXISTS responsable_id INTEGER
  REFERENCES funcionario(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_festival_resp ON festival(responsable_id);

-- ── Formaliza la FK suelta festival.subgrupo_id → subgrupo(id) ───────
-- Los festivales reales apuntan a subgrupo 1 (Cultura); el QA (NULL) ya
-- se borró arriba. NOT VALID evita reescanear la tabla; se valida aparte.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'festival_subgrupo_id_fkey'
    ) THEN
        ALTER TABLE festival
          ADD CONSTRAINT festival_subgrupo_id_fkey
          FOREIGN KEY (subgrupo_id) REFERENCES subgrupo(id) NOT VALID;
        ALTER TABLE festival VALIDATE CONSTRAINT festival_subgrupo_id_fkey;
    END IF;
END $$;

COMMIT;

-- =====================================================================
-- REVERSA (si hay que deshacer):
--   ALTER TABLE festival DROP CONSTRAINT IF EXISTS festival_subgrupo_id_fkey;
--   ALTER TABLE festival DROP COLUMN IF EXISTS responsable_id;
--   ALTER TABLE evento   DROP COLUMN IF EXISTS festival_dia_id;
--   DROP TABLE IF EXISTS festival_dia;
--   (el festival de prueba QA no se restaura — era dato de prueba)
-- =====================================================================
