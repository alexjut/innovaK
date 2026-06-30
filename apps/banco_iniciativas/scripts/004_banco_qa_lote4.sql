-- ============================================================================
-- Banco de Iniciativas #62 — QA Lote 4 (U-05 población + U-07 enfoque_propuesta)
-- Fecha: 2026-06-30 · Rama: feat/banco-qa-#62
--
-- DECISIÓN ALEX: REUSAR catálogos genéricos existentes tal cual; NINGÚN
-- catálogo dedicado nuevo. Solo se crean TABLAS PUENTE (bridges) a los
-- genéricos + columnas booleanas (flags) en la inscripción. 100% aditivo,
-- idempotente, atómico, con ROLLBACK. NO toca las 24 inscripciones reales.
-- NO LO CORRE CLAUDE. Lo revisa/corre Alex tras snapshot. Tablas managed=False.
--
-- ⚠️ REDUCCIONES DE GRANULARIDAD vs el QA (registradas para confirmar con
--    Deportes; si piden el detalle fino, se agrega catálogo dedicado DESPUÉS,
--    aditivo):
--    1. Discapacidad: 8+No aplica  →  7 (taxonomía oficial `tipo_discapacidad`);
--       "No aplica" = sin filas en el puente (lo maneja la UI), no columna.
--    2. Desplazadas transfronterizas: split Migrante/Refugiado → marca única
--       (flag `desplazada_transfronteriza`).
--    3. Habitabilidad en calle: 5 niveles → sí/no (flag `habitante_calle`).
--    4. enfoque_propuesta: "7" → se reusa `enfoque_diferencial` (12 activos)
--       tal cual; más opciones, no menos. Desbloquea el campo pausado de lote 2.
--    5. Poblaciones rurales: 2 categorías (Campesina/o vs Habitante rural)
--       → marca única (flag `poblacion_rural`). No hay genérico de 2 valores;
--       si Deportes necesita distinguir, catálogo dedicado aditivo después.
-- ============================================================================

BEGIN;

-- ── U-05 · flags de población (booleanos nullable; reusan el concepto de los
--    flags genéricos persona.*; viven en la inscripción por ser foco de la ORG) ──
ALTER TABLE inscripcion_banco_iniciativa
    ADD COLUMN IF NOT EXISTS habitante_calle            BOOLEAN,
    ADD COLUMN IF NOT EXISTS victima_conflicto          BOOLEAN,
    ADD COLUMN IF NOT EXISTS poblacion_rural            BOOLEAN,
    ADD COLUMN IF NOT EXISTS desplazada_transfronteriza BOOLEAN;

-- ── Puentes a catálogos GENÉRICOS existentes (sin catálogo nuevo) ───────────
-- orientacion_sexual / identidad_genero / grupo_etnico / tipo_discapacidad
-- tienen codigo INTEGER; enfoque_diferencial tiene codigo SMALLINT.
CREATE TABLE IF NOT EXISTS inscripcion_banco_orientacion_sexual (
    id BIGSERIAL UNIQUE,
    inscripcion_id            BIGINT  NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    orientacion_sexual_codigo INTEGER NOT NULL REFERENCES orientacion_sexual(codigo),
    PRIMARY KEY (inscripcion_id, orientacion_sexual_codigo)
);

CREATE TABLE IF NOT EXISTS inscripcion_banco_identidad_genero (
    id BIGSERIAL UNIQUE,
    inscripcion_id          BIGINT  NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    identidad_genero_codigo INTEGER NOT NULL REFERENCES identidad_genero(codigo),
    PRIMARY KEY (inscripcion_id, identidad_genero_codigo)
);

CREATE TABLE IF NOT EXISTS inscripcion_banco_grupo_etnico (
    id BIGSERIAL UNIQUE,
    inscripcion_id      BIGINT  NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    grupo_etnico_codigo INTEGER NOT NULL REFERENCES grupo_etnico(codigo),
    PRIMARY KEY (inscripcion_id, grupo_etnico_codigo)
);

-- Discapacidad: puente a las 7 de tipo_discapacidad. "No aplica" = sin filas.
CREATE TABLE IF NOT EXISTS inscripcion_banco_discapacidad (
    id BIGSERIAL UNIQUE,
    inscripcion_id          BIGINT  NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    tipo_discapacidad_codigo INTEGER NOT NULL REFERENCES tipo_discapacidad(codigo),
    PRIMARY KEY (inscripcion_id, tipo_discapacidad_codigo)
);

-- U-07 enfoque_propuesta: puente NUEVO al MISMO catálogo enfoque_diferencial
-- (mismo patrón que ciclo_vital↔rango_etario: catálogo compartido, puente
-- separado del de población `inscripcion_banco_enfoque`). Desbloquea U-07.
CREATE TABLE IF NOT EXISTS inscripcion_banco_enfoque_propuesta (
    id BIGSERIAL UNIQUE,
    inscripcion_id BIGINT   NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    enfoque_codigo SMALLINT NOT NULL REFERENCES enfoque_diferencial(codigo),
    PRIMARY KEY (inscripcion_id, enfoque_codigo)
);

COMMIT;

-- ============================================================================
-- ROLLBACK (deshace lote 4; solo objetos nuevos/vacíos; no toca catálogos
-- genéricos ni las 24 filas).
-- ============================================================================
-- BEGIN;
-- DROP TABLE IF EXISTS inscripcion_banco_orientacion_sexual;
-- DROP TABLE IF EXISTS inscripcion_banco_identidad_genero;
-- DROP TABLE IF EXISTS inscripcion_banco_grupo_etnico;
-- DROP TABLE IF EXISTS inscripcion_banco_discapacidad;
-- DROP TABLE IF EXISTS inscripcion_banco_enfoque_propuesta;
-- ALTER TABLE inscripcion_banco_iniciativa
--     DROP COLUMN IF EXISTS habitante_calle,
--     DROP COLUMN IF EXISTS victima_conflicto,
--     DROP COLUMN IF EXISTS poblacion_rural,
--     DROP COLUMN IF EXISTS desplazada_transfronteriza;
-- COMMIT;
