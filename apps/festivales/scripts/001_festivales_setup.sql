-- =====================================================================
-- Módulo Festivales — DDL-1 (catálogo + cabecera + tipo_evento + evento.festival_id)
-- Proyecto 2780 "KENNEDY PROYECTA TALENTO", Meta 4 (KPI 15, eventos 60/15).
-- Ver docs/propuestas/festivales.md.
--
-- APLICAR tras backup < 24 h (~/Proyectos/postgres/backup_postgres.sh).
-- El contenedor innova_k NO tiene psql: aplicar con
--   connection.cursor().execute(open('.../001_festivales_setup.sql').read())
-- REVERSA al final del archivo.
-- =====================================================================
BEGIN;

-- ── Catálogo de tipos de festival ───────────────────────────────────
CREATE TABLE IF NOT EXISTS tipo_festival (
    codigo SMALLINT PRIMARY KEY,
    nombre TEXT NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    orden  SMALLINT
);
INSERT INTO tipo_festival (codigo, nombre, orden) VALUES
 (1,'Rock',10),(2,'Hip Hop',20),(3,'Salsa',30),(4,'Libertad Religiosa',40),
 (5,'Góspel',50),(6,'Vallenato',60),(7,'Popular y Carranga',70),
 (8,'Festival de Festivales',80),(99,'Otro',999)
ON CONFLICT (codigo) DO NOTHING;

-- ── Cabecera del festival ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS festival (
    id BIGSERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    tipo_festival_codigo SMALLINT REFERENCES tipo_festival(codigo),
    vigencia SMALLINT NOT NULL,
    numero_edicion SMALLINT,
    estado VARCHAR(20) NOT NULL DEFAULT 'planeado',
    subgrupo_id INTEGER,
    fecha_inicio DATE,
    fecha_fin DATE,
    lugar_texto TEXT,
    descripcion TEXT,
    documentado BOOLEAN NOT NULL DEFAULT FALSE,
    publicado   BOOLEAN NOT NULL DEFAULT FALSE,
    publicado_en TIMESTAMPTZ,
    slug VARCHAR(80) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_festival_nombre_vigencia UNIQUE (nombre, vigencia),
    CONSTRAINT ck_festival_estado CHECK (estado IN ('planeado','ejecutado','cerrado'))
);
CREATE INDEX IF NOT EXISTS idx_festival_vigencia ON festival(vigencia);
CREATE INDEX IF NOT EXISTS idx_festival_estado   ON festival(estado);
CREATE INDEX IF NOT EXISTS idx_festival_tipo     ON festival(tipo_festival_codigo);

-- ── tipo_evento FESTIVAL (cada acto es un Evento de este tipo) ───────
INSERT INTO tipo_evento (codigo, nombre, descripcion, activo,
   permite_inscripcion, permite_caracterizacion, permite_qr, requiere_actividad_plan)
VALUES ('FESTIVAL', 'Festival cultural',
   'Acto/concierto/novena de un festival de Cultura. Suma al KPI de eventos (Meta 4, proyecto 2780).',
   TRUE, FALSE, FALSE, FALSE, TRUE)
ON CONFLICT (codigo) DO NOTHING;

-- ── DDL-1b: liga cada Evento a su Festival (decisión Alex 2026-06-18) ─
-- 🚨 toca la tabla central `evento` (una sola columna nullable).
ALTER TABLE evento ADD COLUMN IF NOT EXISTS festival_id BIGINT
  REFERENCES festival(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_evento_festival ON evento(festival_id);

COMMIT;

-- =====================================================================
-- REVERSA (si hay que deshacer):
--   ALTER TABLE evento DROP COLUMN IF EXISTS festival_id;
--   DELETE FROM tipo_evento WHERE codigo = 'FESTIVAL';
--   DROP TABLE IF EXISTS festival;
--   DROP TABLE IF EXISTS tipo_festival;
-- =====================================================================
