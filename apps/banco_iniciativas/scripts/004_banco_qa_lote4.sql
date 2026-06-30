-- ============================================================================
-- Banco de Iniciativas #62 — QA Lote 4 (U-05 población + U-07 enfoque_propuesta)
-- Fecha: 2026-06-30 · Rama: feat/banco-qa-#62
-- FUENTE DE VERDAD: documento oficial REQUERIMIENTOS_Y_AJUSTES_DE_DESARROLLO_BI.
--
-- Las reducciones de granularidad de la versión previa SE REVIERTEN: ahora hay
-- listas exactas → catálogos DEDICADOS (no reuso de enfoque_diferencial, no
-- flags para habitabilidad/desplazadas/rurales). Se REUSAN genéricas solo donde
-- el contenido coincide: discapacidad, orientación sexual, identidad de género.
--
-- 100% aditivo, idempotente, atómico, con ROLLBACK. NO toca las 24 inscripciones.
-- NO LO CORRE CLAUDE. Lo revisa/corre Alex tras snapshot. Tablas managed=False.
-- Catálogos dedicados: codigo SMALLINT plano (no IDENTITY) → INSERT directo.
--
-- VERIFICAR EN FORMA/CÓDIGO (no DDL):
--  - orientación: el genérico tiene 7; el doc pide 3 (Heterosexual/Bisexual/
--    Homosexual) → el form filtra a esas 3.
--  - identidad: genérico dice Hombre/Mujer/Persona transgénero; doc dice
--    Masculina/Femenina/Transgénero → CONFIRMAR si se relabela en UI o se hace dedicado.
-- ============================================================================

BEGIN;

-- ── U-05 · víctima del conflicto = binario (doc) → flag booleano ────────────
ALTER TABLE inscripcion_banco_iniciativa
    ADD COLUMN IF NOT EXISTS victima_conflicto BOOLEAN;

-- ── Catálogos DEDICADOS (listas EXACTAS del doc oficial) ────────────────────
CREATE TABLE IF NOT EXISTS enfoque_propuesta (
    codigo SMALLINT PRIMARY KEY, nombre TEXT NOT NULL UNIQUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE, orden SMALLINT);
INSERT INTO enfoque_propuesta (codigo, nombre, orden) VALUES
    (1, 'Enfoque de géneros e identidades diversas', 1),
    (2, 'Enfoque étnico (Afro, Indígenas, Rrom, Raizal, Palenquero)', 2),
    (3, 'Enfoque de inclusión para personas con discapacidad', 3),
    (4, 'Enfoque para víctimas del conflicto armado', 4),
    (5, 'Enfoque para población migrante o transfronteriza', 5),
    (6, 'Enfoque para habitabilidad en calle', 6),
    (7, 'Ninguno / Población general abierta', 7)
ON CONFLICT (codigo) DO NOTHING;

CREATE TABLE IF NOT EXISTS tipo_habitabilidad_calle (
    codigo SMALLINT PRIMARY KEY, nombre TEXT NOT NULL UNIQUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE, orden SMALLINT);
INSERT INTO tipo_habitabilidad_calle (codigo, nombre, orden) VALUES
    (1, 'Habitante de calle', 1),
    (2, 'Personas en calle', 2),
    (3, 'Personas en riesgo de habitar en calle', 3),
    (4, 'Habitabilidad en calle', 4),
    (5, 'Calle', 5),
    (6, 'No aplica', 6)
ON CONFLICT (codigo) DO NOTHING;

CREATE TABLE IF NOT EXISTS tipo_desplazamiento (
    codigo SMALLINT PRIMARY KEY, nombre TEXT NOT NULL UNIQUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE, orden SMALLINT);
INSERT INTO tipo_desplazamiento (codigo, nombre, orden) VALUES
    (1, 'Migrante', 1), (2, 'Refugiado', 2), (3, 'No aplica', 3)
ON CONFLICT (codigo) DO NOTHING;

CREATE TABLE IF NOT EXISTS tipo_poblacion_rural (
    codigo SMALLINT PRIMARY KEY, nombre TEXT NOT NULL UNIQUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE, orden SMALLINT);
INSERT INTO tipo_poblacion_rural (codigo, nombre, orden) VALUES
    (1, 'Campesina(o)', 1), (2, 'Habitante rural', 2), (3, 'No aplica', 3)
ON CONFLICT (codigo) DO NOTHING;

-- Grupos étnicos: el genérico `grupo_etnico` FUSIONA NARP (Afrocolombiano único,
-- sin split Negros/Afrodescendientes) → NO coincide → catálogo dedicado con los 7 del doc.
CREATE TABLE IF NOT EXISTS grupo_etnico_banco (
    codigo SMALLINT PRIMARY KEY, nombre TEXT NOT NULL UNIQUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE, orden SMALLINT);
INSERT INTO grupo_etnico_banco (codigo, nombre, orden) VALUES
    (1, 'Negros/as', 1),
    (2, 'Afrodescendientes/Afrocolombianas', 2),
    (3, 'Palenquero/a', 3),
    (4, 'Indígenas', 4),
    (5, 'Rrom', 5),
    (6, 'Raizal', 6),
    (7, 'No aplica', 7)
ON CONFLICT (codigo) DO NOTHING;

-- ── Puentes a GENÉRICAS reusadas (codigo INTEGER) ───────────────────────────
CREATE TABLE IF NOT EXISTS inscripcion_banco_discapacidad (
    id BIGSERIAL UNIQUE,
    inscripcion_id           BIGINT  NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    tipo_discapacidad_codigo INTEGER NOT NULL REFERENCES tipo_discapacidad(codigo),
    PRIMARY KEY (inscripcion_id, tipo_discapacidad_codigo));

CREATE TABLE IF NOT EXISTS inscripcion_banco_orientacion_sexual (
    id BIGSERIAL UNIQUE,
    inscripcion_id            BIGINT  NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    orientacion_sexual_codigo INTEGER NOT NULL REFERENCES orientacion_sexual(codigo),
    PRIMARY KEY (inscripcion_id, orientacion_sexual_codigo));

CREATE TABLE IF NOT EXISTS inscripcion_banco_identidad_genero (
    id BIGSERIAL UNIQUE,
    inscripcion_id          BIGINT  NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    identidad_genero_codigo INTEGER NOT NULL REFERENCES identidad_genero(codigo),
    PRIMARY KEY (inscripcion_id, identidad_genero_codigo));

-- ── Puentes a catálogos DEDICADOS (codigo SMALLINT) ─────────────────────────
CREATE TABLE IF NOT EXISTS inscripcion_banco_grupo_etnico (
    id BIGSERIAL UNIQUE,
    inscripcion_id      BIGINT   NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    grupo_etnico_codigo SMALLINT NOT NULL REFERENCES grupo_etnico_banco(codigo),
    PRIMARY KEY (inscripcion_id, grupo_etnico_codigo));

CREATE TABLE IF NOT EXISTS inscripcion_banco_enfoque_propuesta (
    id BIGSERIAL UNIQUE,
    inscripcion_id          BIGINT   NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    enfoque_propuesta_codigo SMALLINT NOT NULL REFERENCES enfoque_propuesta(codigo),
    PRIMARY KEY (inscripcion_id, enfoque_propuesta_codigo));

CREATE TABLE IF NOT EXISTS inscripcion_banco_habitabilidad (
    id BIGSERIAL UNIQUE,
    inscripcion_id   BIGINT   NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    habitabilidad_codigo SMALLINT NOT NULL REFERENCES tipo_habitabilidad_calle(codigo),
    PRIMARY KEY (inscripcion_id, habitabilidad_codigo));

CREATE TABLE IF NOT EXISTS inscripcion_banco_desplazamiento (
    id BIGSERIAL UNIQUE,
    inscripcion_id     BIGINT   NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    desplazamiento_codigo SMALLINT NOT NULL REFERENCES tipo_desplazamiento(codigo),
    PRIMARY KEY (inscripcion_id, desplazamiento_codigo));

CREATE TABLE IF NOT EXISTS inscripcion_banco_poblacion_rural (
    id BIGSERIAL UNIQUE,
    inscripcion_id        BIGINT   NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    poblacion_rural_codigo SMALLINT NOT NULL REFERENCES tipo_poblacion_rural(codigo),
    PRIMARY KEY (inscripcion_id, poblacion_rural_codigo));

COMMIT;

-- ============================================================================
-- ROLLBACK (solo objetos nuevos/vacíos; no toca genéricas ni las 24 filas).
-- ============================================================================
-- BEGIN;
-- DROP TABLE IF EXISTS inscripcion_banco_discapacidad;
-- DROP TABLE IF EXISTS inscripcion_banco_orientacion_sexual;
-- DROP TABLE IF EXISTS inscripcion_banco_identidad_genero;
-- DROP TABLE IF EXISTS inscripcion_banco_grupo_etnico;
-- DROP TABLE IF EXISTS inscripcion_banco_enfoque_propuesta;
-- DROP TABLE IF EXISTS inscripcion_banco_habitabilidad;
-- DROP TABLE IF EXISTS inscripcion_banco_desplazamiento;
-- DROP TABLE IF EXISTS inscripcion_banco_poblacion_rural;
-- DROP TABLE IF EXISTS enfoque_propuesta;
-- DROP TABLE IF EXISTS tipo_habitabilidad_calle;
-- DROP TABLE IF EXISTS tipo_desplazamiento;
-- DROP TABLE IF EXISTS tipo_poblacion_rural;
-- DROP TABLE IF EXISTS grupo_etnico_banco;
-- ALTER TABLE inscripcion_banco_iniciativa DROP COLUMN IF EXISTS victima_conflicto;
-- COMMIT;
