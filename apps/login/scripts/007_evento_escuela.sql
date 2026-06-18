-- =====================================================================
-- Cursos ↔ Escuela (sede). Liga el evento/curso a la escuela donde se dicta
-- (las 241 escuelas tienen lat/lon → mapa de calor de oferta formativa).
-- Absorción KDApp PR-2. Aplicar tras backup < 24 h. REVERSA al final.
-- =====================================================================
ALTER TABLE evento ADD COLUMN IF NOT EXISTS escuela_id INTEGER
  REFERENCES escuela(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_evento_escuela ON evento(escuela_id);

-- REVERSA: ALTER TABLE evento DROP COLUMN IF EXISTS escuela_id;
-- =====================================================================
