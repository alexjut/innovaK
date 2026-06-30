-- ============================================================================
-- Banco de Iniciativas #62 — QA Lote 2 (DDL ADITIVO, reversible)
-- Fecha: 2026-06-30 · Rama: feat/banco-qa-#62
--
-- REGLA: 100% aditivo. Ningún DROP/ALTER destructivo. Las 24 inscripciones
-- reales del piloto quedan intactas (snapshot previo:
-- backups/banco_insc62_snapshot_20260630_092722.{dump,csv}).
--
-- NO LO CORRE CLAUDE. Lo revisa y lo corre Alex tras confirmar el snapshot.
-- Tablas managed=False → el DDL va a mano (Django no las gestiona).
--
-- EXCLUIDO de este lote (bloqueado hasta lista oficial): catálogo
-- `enfoque_propuesta` y su tabla puente `inscripcion_banco_enfoque_propuesta`.
-- ============================================================================

BEGIN;

-- ── U-03, U-06, U-07, U-08, M-02 · columnas nuevas (todas NULLABLE) ─────────
ALTER TABLE inscripcion_banco_iniciativa
    ADD COLUMN IF NOT EXISTS tamano_organizacion        VARCHAR(20),   -- U-03 (choices app)
    ADD COLUMN IF NOT EXISTS composicion_organizacion   VARCHAR(40),   -- U-03 (choices app)
    ADD COLUMN IF NOT EXISTS actividad_principal        VARCHAR(150),  -- U-03
    ADD COLUMN IF NOT EXISTS participa_espacio          BOOLEAN,       -- U-06 (Sí/No)
    ADD COLUMN IF NOT EXISTS espacio_participacion      VARCHAR(60),   -- U-06 (choices app)
    ADD COLUMN IF NOT EXISTS espacio_participacion_otro VARCHAR(50),   -- U-06 ("Otro")
    ADD COLUMN IF NOT EXISTS enfoque_genero_mujer       BOOLEAN,       -- U-07 (Sí/No)
    ADD COLUMN IF NOT EXISTS personas_beneficiar        VARCHAR(20),   -- U-07 (choices app)
    ADD COLUMN IF NOT EXISTS nombre_espacio_ejecucion   VARCHAR(50),   -- U-07
    ADD COLUMN IF NOT EXISTS direccion_espacio_ejecucion VARCHAR(50),  -- U-07
    ADD COLUMN IF NOT EXISTS requerimiento_detalle      TEXT,          -- U-08 (detalle/cantidad)
    ADD COLUMN IF NOT EXISTS barrio_texto               VARCHAR(120);  -- M-02 (conserva barrio_codigo legacy)

-- ── Catálogos nuevos (patrón codigo/nombre/activo/orden) ────────────────────
-- U-08: tipo de apoyo solicitado (5)
CREATE TABLE IF NOT EXISTS tipo_apoyo (
    codigo SMALLINT PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    orden  SMALLINT
);
INSERT INTO tipo_apoyo (codigo, nombre, orden) VALUES
    (1, 'Apoyo logístico', 1),
    (2, 'Formación o capacitación', 2),
    (3, 'Eventos o torneos', 3),
    (4, 'Infraestructura', 4),
    (5, 'Implementación deportiva', 5)
ON CONFLICT (codigo) DO NOTHING;

-- U-08: categorías de materiales (condicional a "Implementación deportiva") (6)
CREATE TABLE IF NOT EXISTS categoria_material (
    codigo SMALLINT PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    orden  SMALLINT
);
INSERT INTO categoria_material (codigo, nombre, orden) VALUES
    (1, 'Implementos deportivos de campo', 1),
    (2, 'Material deportivo especializado', 2),
    (3, 'Equipo tecnológico y digital', 3),
    (4, 'Logística y eventos', 4),
    (5, 'Seguridad y señalización', 5),
    (6, 'Otros materiales', 6)
ON CONFLICT (codigo) DO NOTHING;

-- ── Tablas puente nuevas (id BIGSERIAL UNIQUE + PK compuesta, patrón módulo) ─
-- U-07: ciclo vital de la propuesta → REUSA el catálogo rango_etario (M-05),
-- misma fuente canónica de 7 grupos; puente separado del de población (Paso 5).
CREATE TABLE IF NOT EXISTS inscripcion_banco_ciclo_vital (
    id BIGSERIAL UNIQUE,
    inscripcion_id      BIGINT   NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    rango_etario_codigo SMALLINT NOT NULL REFERENCES rango_etario(codigo),
    PRIMARY KEY (inscripcion_id, rango_etario_codigo)
);

-- U-07: entorno/red donde se desarrolla → REUSA las 4 redes de escenario.categoria_pot
-- (sin catálogo nuevo; CHECK enumera los 4 valores válidos, el 4º lo crea U-04).
CREATE TABLE IF NOT EXISTS inscripcion_banco_entorno_red (
    id BIGSERIAL UNIQUE,
    inscripcion_id BIGINT      NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    red_codigo     VARCHAR(40) NOT NULL
        CHECK (red_codigo IN ('red_estructurante','red_proximidad','otros_dotacionales','otros_practica')),
    PRIMARY KEY (inscripcion_id, red_codigo)
);

-- U-08: tipo de apoyo (M2M)
CREATE TABLE IF NOT EXISTS inscripcion_banco_tipo_apoyo (
    id BIGSERIAL UNIQUE,
    inscripcion_id    BIGINT   NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    tipo_apoyo_codigo SMALLINT NOT NULL REFERENCES tipo_apoyo(codigo),
    PRIMARY KEY (inscripcion_id, tipo_apoyo_codigo)
);

-- U-08: categorías de material (M2M, condicional)
CREATE TABLE IF NOT EXISTS inscripcion_banco_categoria_material (
    id BIGSERIAL UNIQUE,
    inscripcion_id          BIGINT   NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    categoria_material_codigo SMALLINT NOT NULL REFERENCES categoria_material(codigo),
    PRIMARY KEY (inscripcion_id, categoria_material_codigo)
);

COMMIT;

-- ============================================================================
-- ROLLBACK (revierte TODO lo de este lote; ejecutar solo si hay que deshacer).
-- Las tablas puente se borran antes que los catálogos (por las FK).
-- ============================================================================
-- BEGIN;
-- DROP TABLE IF EXISTS inscripcion_banco_ciclo_vital;
-- DROP TABLE IF EXISTS inscripcion_banco_entorno_red;
-- DROP TABLE IF EXISTS inscripcion_banco_tipo_apoyo;
-- DROP TABLE IF EXISTS inscripcion_banco_categoria_material;
-- DROP TABLE IF EXISTS tipo_apoyo;
-- DROP TABLE IF EXISTS categoria_material;
-- ALTER TABLE inscripcion_banco_iniciativa
--     DROP COLUMN IF EXISTS tamano_organizacion,
--     DROP COLUMN IF EXISTS composicion_organizacion,
--     DROP COLUMN IF EXISTS actividad_principal,
--     DROP COLUMN IF EXISTS participa_espacio,
--     DROP COLUMN IF EXISTS espacio_participacion,
--     DROP COLUMN IF EXISTS espacio_participacion_otro,
--     DROP COLUMN IF EXISTS enfoque_genero_mujer,
--     DROP COLUMN IF EXISTS personas_beneficiar,
--     DROP COLUMN IF EXISTS nombre_espacio_ejecucion,
--     DROP COLUMN IF EXISTS direccion_espacio_ejecucion,
--     DROP COLUMN IF EXISTS requerimiento_detalle,
--     DROP COLUMN IF EXISTS barrio_texto;
-- COMMIT;
