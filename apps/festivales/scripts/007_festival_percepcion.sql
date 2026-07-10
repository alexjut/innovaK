-- =====================================================================
-- Módulo Festivales — DDL-G (PR-G · Encuesta de percepción ciudadana)
-- Decisión Alex 2026-07-10:
--   - UN cuestionario general para TODOS los festivales (percepción de
--     impacto cultural/social/identidad). Lo llena el asistente por QR.
--   - "Publicar el festival = activar la encuesta": el endpoint público
--     solo acepta respuestas si festival.publicado = TRUE (igual que la
--     ficha pública). No hay interruptor aparte.
--   - Instrumento de percepción con MUCHAS respuestas por festival: NO es
--     captura de beneficiarios y NO suma a ningún KPI.
--
-- Las respuestas se guardan como JSONB (motor data-driven; las preguntas
-- viven en apps/festivales/services/percepcion_schema.py). Columnas fijas
-- para búsqueda/dedup/matrices. Sin flujo de validación (percepción
-- estadística), por eso no hay `estado`.
--
-- APLICAR tras backup < 24 h. Sin psql en el contenedor:
--   connection.cursor().execute(open('.../007_festival_percepcion.sql').read())
-- REVERSA al final.
-- =====================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS festival_percepcion (
    id BIGSERIAL PRIMARY KEY,
    festival_id BIGINT NOT NULL REFERENCES festival(id) ON DELETE CASCADE,
    datos JSONB NOT NULL DEFAULT '{}'::jsonb,       -- todas las respuestas
    numero_documento VARCHAR(30),                    -- para dedup/búsqueda
    nombre TEXT,                                     -- nombre_completo (búsqueda)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_festival_percep_festival ON festival_percepcion(festival_id);
CREATE INDEX IF NOT EXISTS idx_festival_percep_datos    ON festival_percepcion USING GIN (datos);
-- Una cédula no responde dos veces la encuesta del MISMO festival (los
-- anónimos/sin documento sí pueden, no rompen el índice parcial).
CREATE UNIQUE INDEX IF NOT EXISTS uq_festival_percep_doc
  ON festival_percepcion(festival_id, numero_documento) WHERE numero_documento IS NOT NULL;

COMMIT;

-- =====================================================================
-- REVERSA (si hay que deshacer):
--   BEGIN;
--   DROP TABLE IF EXISTS festival_percepcion;
--   COMMIT;
-- =====================================================================
