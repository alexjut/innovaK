-- =====================================================================
-- Capa CAI (Comando de Atención Inmediata) — Seguridad
--
-- FUENTE (verificada 2026-08-05, sin API key):
--   oaiee.scj.gov.co/agc/rest/services/Tematicos_NR/
--   EquipamientoPMSDSCJ/MapServer/22  — Secretaría Distrital de Seguridad,
--   Convivencia y Justicia. Kennedy (CAIIULOCAL='08'): 15 CAI con código,
--   nombre, dirección, teléfono, UPZ y coordenada.
--
-- SOBRE FIJOS Y MÓVILES — la razón de que exista la columna `tipo`:
--   La capa oficial SÍ conoce la distinción: el dominio de CAIIULOCAL trae el
--   código '00' = MOVILES. Pero hoy devuelve CERO registros móviles en toda
--   Bogotá; los 158 publicados (15 en Kennedy) son fijos. O sea: el móvil no
--   se puede sincronizar, hay que cargarlo a mano.
--   Por eso `tipo` es una columna y no un cálculo: un CAI móvil cargado por
--   Seguridad tiene que poder convivir con los 15 sincronizados sin que el
--   sync lo borre y sin que el mapa los pinte igual. `fuente` es lo que los
--   separa: 'SCJ' lo maneja el sync, 'MANUAL' no se toca.
--
-- APLICAR tras backup < 24 h (~/Proyectos/postgres/backup_postgres.sh).
-- El contenedor innova_k NO tiene psql: aplicar con
--   connection.cursor().execute(open('.../020_cai_seguridad.sql').read())
-- REVERSA al final del archivo.
-- =====================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS cai (
    id BIGSERIAL PRIMARY KEY,

    -- Código oficial del CAI (E08C01…E08C15 en Kennedy). Para los móviles
    -- cargados a mano el área define el suyo; por eso es TEXT y no un patrón.
    codigo VARCHAR(16) NOT NULL UNIQUE,
    nombre TEXT NOT NULL,

    tipo VARCHAR(8) NOT NULL DEFAULT 'FIJO',

    direccion TEXT,
    telefono  TEXT,
    horario   TEXT,
    email     TEXT,

    localidad_codigo INTEGER,
    -- La capa entrega 'UPZ44'; el sync guarda el 44 y deja el texto en
    -- `properties` por si el formato cambia.
    upz_codigo INTEGER,

    latitud  NUMERIC(9,6),
    longitud NUMERIC(9,6),

    activo BOOLEAN NOT NULL DEFAULT TRUE,

    -- 'SCJ' = lo trae el sync y el sync lo puede pisar.
    -- 'MANUAL' = lo cargó el área; el sync NO lo toca.
    fuente      VARCHAR(20) NOT NULL DEFAULT 'SCJ',
    fecha_corte DATE,
    properties  JSONB,
    synced_at   TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ck_cai_tipo   CHECK (tipo   IN ('FIJO', 'MOVIL')),
    CONSTRAINT ck_cai_fuente CHECK (fuente IN ('SCJ', 'MANUAL'))
);

CREATE INDEX IF NOT EXISTS idx_cai_localidad ON cai (localidad_codigo);
CREATE INDEX IF NOT EXISTS idx_cai_tipo      ON cai (tipo);
-- Parcial: el mapa solo consulta los que tienen punto.
CREATE INDEX IF NOT EXISTS idx_cai_geo
    ON cai (latitud, longitud) WHERE latitud IS NOT NULL;

COMMIT;

-- =====================================================================
-- REVERSA (si hay que deshacer):
--   DROP TABLE IF EXISTS cai;
-- =====================================================================
