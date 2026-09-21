-- 029 — Modificaciones de contrato y las columnas que faltaban del espejo.
--
-- LO QUE PIDIÓ EL EQUIPO QUE CONSUME LA API, y qué hay de cada cosa:
--
--   · fechas y valores separados (inicial vs actual, días adicionados,
--     duración) → el dataset de origen SÍ los trae: `dias_adicionados` y
--     `duraci_n_del_contrato` estaban entre los 81 campos que ofrece y
--     nosotros solo traíamos 20. Se agregan al espejo.
--   · modificaciones por contrato → tabla nueva. Se arman con DOS datasets
--     de SECOP, no con los tres que nos pasaron: `u99c-7mfm` devuelve CERO
--     filas para los contratos de Kennedy (medido), así que no se ingiere.
--
--   u8cx-r425  el detalle: días extendidos, valor, fechas, estado, propósito
--   cb9c-h8sn  el TIPO (MODIFICACION GENERAL / CESION), que el otro no trae
--
-- Se unen por `u8cx-r425.identificador_modificacion = cb9c-h8sn.identificador`
-- (`CO1.CTRMOD.…`). Ojo: `cb9c-h8sn` publica la MISMA fila repetida, así que
-- la llave única es el identificador de la modificación y no el par.
--
-- Lo que estos datasets NO traen, y por eso no se promete: el proveedor
-- ANTERIOR y el NUEVO de una cesión. El cambio de contratista solo aparece
-- descrito en el texto libre de `proposito_modificacion`. Inventarlo
-- parseando prosa sería peor que decir que no está.

BEGIN;

-- ── Columnas nuevas del espejo ───────────────────────────────────────
ALTER TABLE secop_contrato
    ADD COLUMN IF NOT EXISTS dias_adicionados    integer,
    ADD COLUMN IF NOT EXISTS duracion_contrato   text,
    -- Tipo de documento del proveedor (CC, NIT, CE…). Hace falta para el
    -- endpoint interno de identificación: un número sin su tipo no
    -- identifica a nadie.
    ADD COLUMN IF NOT EXISTS tipo_doc_proveedor  text;

COMMENT ON COLUMN secop_contrato.dias_adicionados IS
    'Días agregados al plazo por modificaciones. De aquí sale la fecha fin INICIAL: fecha_fin - dias_adicionados.';
COMMENT ON COLUMN secop_contrato.tipo_doc_proveedor IS
    'Tipo de documento del contratista. NO se publica en la API abierta para personas naturales.';

-- ── Modificaciones ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS secop_modificacion (
    id                      bigserial PRIMARY KEY,
    -- Identidad de la modificación en SECOP (`CO1.CTRMOD.21858973`). Es la
    -- llave natural: `u8cx-r425` puede traer varias VERSIONES de la misma
    -- modificación y `cb9c-h8sn` la repite tal cual.
    identificador           text NOT NULL,
    id_contrato             text NOT NULL,
    tipo                    text,
    estado                  text,
    descripcion             text,
    proposito               text,
    fecha_aprobacion        date,
    fecha_creacion          date,
    -- Las fechas del contrato DESPUÉS de esta modificación.
    fecha_inicio_contrato   date,
    fecha_fin_contrato      date,
    dias_extendidos         integer,
    valor_modificacion      numeric(18,2),
    numero_version          text,
    fuente                  text,
    hash_fila               text,
    synced_at               timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_secop_modificacion UNIQUE (identificador)
);

CREATE INDEX IF NOT EXISTS ix_secop_modificacion_contrato
    ON secop_modificacion (id_contrato);
CREATE INDEX IF NOT EXISTS ix_secop_modificacion_tipo
    ON secop_modificacion (tipo);

COMMENT ON TABLE secop_modificacion IS
    'Modificaciones de contrato de SECOP II (u8cx-r425 + cb9c-h8sn). Una fila por modificación, no por versión.';
COMMENT ON COLUMN secop_modificacion.estado IS
    'Estado en SECOP. «En Edición» es un BORRADOR: no se debe leer como modificación en firme.';

COMMIT;
