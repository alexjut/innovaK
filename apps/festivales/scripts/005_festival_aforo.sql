-- =====================================================================
-- Módulo Festivales — DDL-D (PR-D · Aforo + asistencia por QR)
-- Decisiones Alex 2026-06-25: QR POR ACTO, aforo = contador + caracterización
-- opcional, aforo proyectado POR ACTO.
--
-- Cada scan del QR del acto registra una fila en festival_asistencia
-- (contador en tiempo real). La caracterización mínima es opcional
-- (asistente anónimo = fila sin documento). El KPI 'eventos' lo sigue
-- contando el acto (PR-C); el aforo es una métrica de asistencia aparte.
--
-- APLICAR tras backup < 24 h. Sin psql en el contenedor:
--   connection.cursor().execute(open('.../005_festival_aforo.sql').read())
-- REVERSA al final.
-- =====================================================================
BEGIN;

-- Aforo proyectado por acto (columna aditiva en la tabla central evento).
ALTER TABLE evento ADD COLUMN IF NOT EXISTS aforo_proyectado INTEGER;

-- Asistencia (contador + caracterización mínima opcional).
CREATE TABLE IF NOT EXISTS festival_asistencia (
    id BIGSERIAL PRIMARY KEY,
    evento_id BIGINT NOT NULL REFERENCES evento(id) ON DELETE CASCADE,
    festival_id BIGINT REFERENCES festival(id) ON DELETE SET NULL,  -- denorm
    documento VARCHAR(30),
    nombre TEXT,
    sexo VARCHAR(10),
    rango_etario_codigo SMALLINT,
    localidad_texto TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_festival_asist_evento   ON festival_asistencia(evento_id);
CREATE INDEX IF NOT EXISTS idx_festival_asist_festival ON festival_asistencia(festival_id);
-- Un mismo documento no se cuenta dos veces en el mismo acto (los anónimos sí).
CREATE UNIQUE INDEX IF NOT EXISTS uq_festival_asist_doc
  ON festival_asistencia(evento_id, documento) WHERE documento IS NOT NULL;

-- El acto de festival expone QR (para el aforo).
UPDATE tipo_evento SET permite_qr = TRUE WHERE codigo = 'FESTIVAL';

COMMIT;

-- =====================================================================
-- REVERSA:
--   ALTER TABLE evento DROP COLUMN IF EXISTS aforo_proyectado;
--   DROP TABLE IF EXISTS festival_asistencia;
--   UPDATE tipo_evento SET permite_qr = FALSE WHERE codigo = 'FESTIVAL';
-- =====================================================================
