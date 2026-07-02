-- ============================================================================
-- Banco de Iniciativas — Motor de puntaje v3: comité BINARIO (una nota)
-- Fecha: 2026-07-02 · Rama: feat/banco-puntaje-pr1
--
-- Cambio de modelo: el comité deja de ser multi-evaluador con promedio y pasa a
-- UNA nota binaria (sí/no) puesta por una persona. La nota vive en la CABECERA
-- (banco_evaluacion_inscripcion, ya 1:1 por inscripción). Se retira la tabla
-- por-evaluador×criterio y el contador n_evaluadores.
--
-- 100% seguro sobre datos: banco_evaluacion_comite_criterio está VACÍA (solo tuvo
-- filas de test, ya limpiadas). Aditivo en la cabecera (columnas nullable).
-- NO toca inscripciones ni catálogos. Atómico, con ROLLBACK.
-- NO LO CORRE CLAUDE: requiere OK de Alex + backup (BD compartida).
-- ============================================================================

BEGIN;

-- Nota del comité en la cabecera (una por inscripción).
ALTER TABLE banco_evaluacion_inscripcion
    ADD COLUMN IF NOT EXISTS viabilidad_cumple  BOOLEAN,     -- sí=15 / no=0
    ADD COLUMN IF NOT EXISTS ambiental_cumple   BOOLEAN,     -- sí=10 / no=0
    ADD COLUMN IF NOT EXISTS innovacion_cumple  BOOLEAN,     -- sí=10 / no=0
    ADD COLUMN IF NOT EXISTS bono_mujeres       BOOLEAN,     -- toggle del bono (+5)
    ADD COLUMN IF NOT EXISTS evaluador_id       INTEGER REFERENCES usuario(id),  -- quién puntuó
    ADD COLUMN IF NOT EXISTS comite_observacion TEXT,
    ADD COLUMN IF NOT EXISTS comite_at          TIMESTAMPTZ; -- cuándo se puntuó

-- Ya no se usa (modelo multi-evaluador retirado).
ALTER TABLE banco_evaluacion_inscripcion DROP COLUMN IF EXISTS n_evaluadores;

-- Tabla por-evaluador×criterio: se elimina (vacía, sin datos reales).
DROP TABLE IF EXISTS banco_evaluacion_comite_criterio;

COMMIT;

-- ============================================================================
-- ROLLBACK
-- ============================================================================
-- BEGIN;
-- ALTER TABLE banco_evaluacion_inscripcion
--     DROP COLUMN IF EXISTS viabilidad_cumple, DROP COLUMN IF EXISTS ambiental_cumple,
--     DROP COLUMN IF EXISTS innovacion_cumple, DROP COLUMN IF EXISTS bono_mujeres,
--     DROP COLUMN IF EXISTS evaluador_id, DROP COLUMN IF EXISTS comite_observacion,
--     DROP COLUMN IF EXISTS comite_at,
--     ADD COLUMN IF NOT EXISTS n_evaluadores SMALLINT NOT NULL DEFAULT 0;
-- CREATE TABLE IF NOT EXISTS banco_evaluacion_comite_criterio (
--     id BIGSERIAL PRIMARY KEY,
--     evaluacion_id BIGINT NOT NULL REFERENCES banco_evaluacion_inscripcion(id) ON DELETE CASCADE,
--     evaluador_id INTEGER NOT NULL REFERENCES usuario(id),
--     criterio_codigo VARCHAR(20) NOT NULL, puntaje NUMERIC(6,2) NOT NULL DEFAULT 0,
--     puntaje_max NUMERIC(6,2) NOT NULL, observacion TEXT NULL,
--     created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
--     CONSTRAINT uq_banco_eval_comite UNIQUE (evaluacion_id, evaluador_id, criterio_codigo));
-- COMMIT;
