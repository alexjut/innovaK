-- ============================================================================
-- Banco de Iniciativas #62 — Motor de puntaje PR-1 (evaluación)
-- Fecha: 2026-07-02 · Rama: feat/banco-puntaje-pr1
--
-- 3 tablas: rúbrica versionada (snapshot inmutable de la config usada) +
-- evaluación por inscripción (cabecera: auto/comité/bono/total/estado/ranking) +
-- criterio de comité por evaluador (se promedia; mín 3 evaluadores para
-- "completo"). El bloque AUTO (30) lo calcula el aplicativo idempotente desde
-- el form; el bloque COMITÉ (70) + bono lo llena/confirma el comité.
--
-- 100% aditivo (tablas nuevas). NO toca inscripciones ni catálogos. Atómico,
-- idempotente, con ROLLBACK. NO LO CORRE CLAUDE: lo revisa/corre Alex tras backup.
-- BIGSERIAL (sin MAX+1), managed=False, sin prefijo public.
-- ============================================================================

BEGIN;

-- Snapshot inmutable de la rúbrica usada (transparencia / defendible ante
-- impugnación). La config vive en services/puntaje.py; al activar una versión
-- se guarda aquí su JSON completo. `evaluacion` referencia la versión.
CREATE TABLE IF NOT EXISTS banco_rubrica (
    version     VARCHAR(20) PRIMARY KEY,       -- 'v1', 'v2', ...
    nombre      TEXT NOT NULL,
    config      JSONB NOT NULL,                -- snapshot de pesos/tiers/reglas
    activa      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Cabecera de evaluación: 1:1 con la inscripción postulada.
CREATE TABLE IF NOT EXISTS banco_evaluacion_inscripcion (
    id                       BIGSERIAL PRIMARY KEY,
    inscripcion_id           BIGINT NOT NULL
                             REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    rubrica_version          VARCHAR(20) NOT NULL REFERENCES banco_rubrica(version),
    puntaje_auto             NUMERIC(6,2) NOT NULL DEFAULT 0,   -- 30 (antigüedad+territorio+capacidad)
    puntaje_comite           NUMERIC(6,2) NULL,                 -- 70 (promedio de evaluadores)
    bono_genero              NUMERIC(4,2) NOT NULL DEFAULT 0,   -- 5 (confirma comité)
    total                    NUMERIC(6,2) NULL,                 -- auto+comite+bono
    -- desglose AUTO legible (transparencia) — [{criterio,pts,max,detalle}]
    auto_detalle             JSONB NULL,
    estado                   VARCHAR(20) NOT NULL DEFAULT 'pendiente',
                             -- pendiente | auto_calculado | en_comite | completo
    n_evaluadores            SMALLINT NOT NULL DEFAULT 0,       -- para el gate "completo" (>=3)
    ranking_pos              INTEGER NULL,
    caracterizacion_at       TIMESTAMPTZ NULL,
    finalizado_at            TIMESTAMPTZ NULL,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_banco_eval_inscripcion UNIQUE (inscripcion_id)
);
CREATE INDEX IF NOT EXISTS idx_banco_eval_estado ON banco_evaluacion_inscripcion(estado);
CREATE INDEX IF NOT EXISTS idx_banco_eval_total  ON banco_evaluacion_inscripcion(total DESC);

-- Puntaje del comité, por EVALUADOR × CRITERIO (se promedia; mín 3 evaluadores).
CREATE TABLE IF NOT EXISTS banco_evaluacion_comite_criterio (
    id               BIGSERIAL PRIMARY KEY,
    evaluacion_id    BIGINT NOT NULL
                     REFERENCES banco_evaluacion_inscripcion(id) ON DELETE CASCADE,
    -- FK formal a usuario: el evaluador es un usuario real del comité. Sin
    -- ON DELETE → no se puede borrar un usuario con puntajes (desactivar en su
    -- lugar); preserva la auditoría de quién puntuó (plata pública).
    evaluador_id     INTEGER NOT NULL REFERENCES usuario(id),
    criterio_codigo  VARCHAR(20) NOT NULL,      -- 'C4_viabilidad', 'C5_ambiental', ...
    puntaje          NUMERIC(6,2) NOT NULL DEFAULT 0,
    puntaje_max      NUMERIC(6,2) NOT NULL,
    observacion      TEXT NULL,                 -- justificación del evaluador
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- un evaluador puntúa cada criterio UNA vez (editable vía upsert).
    CONSTRAINT uq_banco_eval_comite UNIQUE (evaluacion_id, evaluador_id, criterio_codigo)
);
CREATE INDEX IF NOT EXISTS idx_banco_eval_comite_eval ON banco_evaluacion_comite_criterio(evaluacion_id);

COMMIT;

-- ============================================================================
-- ROLLBACK
-- ============================================================================
-- DROP TABLE IF EXISTS banco_evaluacion_comite_criterio;
-- DROP TABLE IF EXISTS banco_evaluacion_inscripcion;
-- DROP TABLE IF EXISTS banco_rubrica;
