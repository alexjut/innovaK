-- =====================================================================
-- Módulo Festivales — DDL-B (PR-B · Biblioteca / evidencias)
-- Repositorio de evidencias por festival (y opcionalmente por día):
-- fotos, videos, actas, listados de asistencia, soportes. El binario va
-- CIFRADO a MongoDB (pipeline mongo_storage); aquí solo el puntero + metadata.
--
-- APLICAR tras backup < 24 h. El contenedor innova_k NO tiene psql:
--   connection.cursor().execute(open('.../004_festival_biblioteca.sql').read())
-- REVERSA al final.
-- =====================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS festival_archivo (
    id BIGSERIAL PRIMARY KEY,
    festival_id BIGINT NOT NULL REFERENCES festival(id) ON DELETE CASCADE,
    festival_dia_id BIGINT REFERENCES festival_dia(id) ON DELETE SET NULL,
    tipo VARCHAR(20) NOT NULL DEFAULT 'foto',
    mongo_id VARCHAR(64) NOT NULL,        -- puntero al doc cifrado en Mongo
    nombre_archivo TEXT,
    mime VARCHAR(120),
    tamano_bytes BIGINT,
    descripcion TEXT,
    subido_por_id INTEGER REFERENCES funcionario(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_festival_archivo_tipo
      CHECK (tipo IN ('foto','video','acta','listado','soporte'))
);
CREATE INDEX IF NOT EXISTS idx_festival_archivo_festival ON festival_archivo(festival_id);
CREATE INDEX IF NOT EXISTS idx_festival_archivo_dia      ON festival_archivo(festival_dia_id);
CREATE INDEX IF NOT EXISTS idx_festival_archivo_tipo     ON festival_archivo(tipo);

COMMIT;

-- =====================================================================
-- REVERSA:
--   DROP TABLE IF EXISTS festival_archivo;
--   (los blobs cifrados en Mongo se limpian aparte con mongo_storage.borrar)
-- =====================================================================
