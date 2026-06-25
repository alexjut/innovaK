-- =====================================================================
-- Módulo Festivales — DDL-E (PR-E · Lineup + jurados + criterios + evaluación)
-- Decisiones Alex 2026-06-18: jurado = funcionario TRANSCRIBE (sin login),
-- consolidado = promedio ponderado por peso, criterios POR FESTIVAL,
-- cierre cuando festival.estado='cerrado'.
--
-- APLICAR tras backup < 24 h. Sin psql en el contenedor:
--   connection.cursor().execute(open('.../006_festival_evaluacion.sql').read())
-- REVERSA al final.
-- =====================================================================
BEGIN;

-- ── Lineup: artistas / grupos / invitados ────────────────────────────
CREATE TABLE IF NOT EXISTS festival_artista (
    id BIGSERIAL PRIMARY KEY,
    festival_id BIGINT NOT NULL REFERENCES festival(id) ON DELETE CASCADE,
    festival_dia_id BIGINT REFERENCES festival_dia(id) ON DELETE SET NULL,
    nombre TEXT NOT NULL,
    tipo VARCHAR(20) NOT NULL DEFAULT 'artista',  -- artista/grupo/invitado
    persona_id INTEGER REFERENCES persona(id) ON DELETE SET NULL,
    organizacion_id INTEGER REFERENCES organizacion(id) ON DELETE SET NULL,
    descripcion TEXT,
    orden SMALLINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_festival_artista_tipo CHECK (tipo IN ('artista','grupo','invitado'))
);
CREATE INDEX IF NOT EXISTS idx_festival_artista_festival ON festival_artista(festival_id);
CREATE INDEX IF NOT EXISTS idx_festival_artista_dia      ON festival_artista(festival_dia_id);

-- ── Jurados (funcionario transcribe; no login de jurado) ─────────────
CREATE TABLE IF NOT EXISTS festival_jurado (
    id BIGSERIAL PRIMARY KEY,
    festival_id BIGINT NOT NULL REFERENCES festival(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    persona_id INTEGER REFERENCES persona(id) ON DELETE SET NULL,
    perfil TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_festival_jurado_festival ON festival_jurado(festival_id);

-- ── Criterios de evaluación (por festival, con peso) ─────────────────
CREATE TABLE IF NOT EXISTS festival_criterio (
    id BIGSERIAL PRIMARY KEY,
    festival_id BIGINT NOT NULL REFERENCES festival(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    peso NUMERIC(5,2) NOT NULL DEFAULT 1,
    orden SMALLINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_festival_criterio_festival ON festival_criterio(festival_id);

-- ── Evaluación: un puntaje por (artista, jurado, criterio) ───────────
CREATE TABLE IF NOT EXISTS festival_evaluacion (
    id BIGSERIAL PRIMARY KEY,
    festival_artista_id BIGINT NOT NULL REFERENCES festival_artista(id) ON DELETE CASCADE,
    festival_jurado_id  BIGINT NOT NULL REFERENCES festival_jurado(id)  ON DELETE CASCADE,
    festival_criterio_id BIGINT NOT NULL REFERENCES festival_criterio(id) ON DELETE CASCADE,
    puntaje NUMERIC(5,2) NOT NULL,
    observacion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_festival_evaluacion UNIQUE (festival_artista_id, festival_jurado_id, festival_criterio_id)
);
CREATE INDEX IF NOT EXISTS idx_festival_eval_artista ON festival_evaluacion(festival_artista_id);

COMMIT;

-- =====================================================================
-- REVERSA:
--   DROP TABLE IF EXISTS festival_evaluacion;
--   DROP TABLE IF EXISTS festival_criterio;
--   DROP TABLE IF EXISTS festival_jurado;
--   DROP TABLE IF EXISTS festival_artista;
-- =====================================================================
