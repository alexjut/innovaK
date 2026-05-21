-- ============================================================================
-- 001_jovenes_setup.sql
-- Módulo "Jóvenes a la E" — Becas (subgrupo Educación, id=8)
-- ============================================================================
-- Fecha:        2026-05-21
-- Autor:        Claude + Alex
-- Backup:       hacer primero `~/Proyectos/postgres/backup_postgres.sh`.
-- Reversa:      bloque comentado al final.
--
-- Contexto (planilla externa 2026-05-21):
--   El proyecto del subgrupo Educación tiene 2 sub-flujos de entrega:
--
--     A) ENTREGA DE BECAS (convenio 773-2025 ADICION)
--        Beneficiario = persona estudiante.
--        Meta 23771 ACCESO:        700 estudiantes en educación posmedia.
--        Meta 23772 PERMANENCIA:   700 estudiantes con apoyo de sostenimiento.
--        --> Este script crea su tabla específica `entrega_beca` y un
--            tipo_evento `JOVENES_BECA` con QR público.
--
--     B) ENTREGA DE DOTACIÓN A SEDE (convenio 955-2025, meta 23773)
--        --> Alex decisión 2026-05-21: NO crear tabla nueva. Reusar el
--            tipo_evento `ENTREGA` (suministros) que ya existe en BD,
--            registrando los actos vía la UI estándar de eventos. Por
--            eso este script NO toca dotación.
--
-- Conexión con el modelo de presupuesto:
--   tipo_evento (JOVENES_BECA, requiere_actividad_plan=TRUE)
--        └── Evento → ActividadPlan → Indicador → MetaProyecto → Proyecto
--                                    (KPI 23771/23772 acceso/permanencia)
--
-- TODO post-DDL (vía UI de presupuesto, fuera de este script):
--   1. Crear/verificar las metas 23771 y 23772 en `metas` + filas en
--      `meta_proyecto` vinculadas al proyecto Educación.
--   2. Crear los KPIs en `presu_indicador_meta_proyecto` (Acceso=700,
--      Permanencia=700).
--   3. Crear `actividad_plan` para el convenio 773-2025 y vincularla
--      a sus KPIs vía `actividad_indicador`.
--   4. Crear evento de captura tipo `JOVENES_BECA` ligado a esa
--      actividad_plan — el QR se genera al guardar.
-- ============================================================================

BEGIN;

-- ─────────────────────────────────────────────────────────────────────
-- 1. Catálogo: elemento entregable a persona (becas)
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS elemento_dotacion (
    codigo     SMALLINT      PRIMARY KEY,
    nombre     TEXT          NOT NULL,
    categoria  VARCHAR(30)   NULL,            -- academico / general
    activo     BOOLEAN       NOT NULL DEFAULT TRUE,
    orden      SMALLINT      NULL
);

COMMENT ON TABLE elemento_dotacion IS
  'Catálogo de elementos entregables en becas a personas (apoyo a metas '
  '23771 acceso / 23772 permanencia del programa Jóvenes a la E).';

INSERT INTO elemento_dotacion (codigo, nombre, categoria, orden) VALUES
    (1, 'Kit académico (libros y útiles)',  'academico', 10),
    (2, 'Apoyo de sostenimiento mensual',   'academico', 20),
    (3, 'Matrícula posmedia',               'academico', 30),
    (4, 'Bono de transporte',               'general',   40),
    (5, 'Bono de alimentación',             'general',   50)
ON CONFLICT (codigo) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────
-- 2. Cabecera: entrega de beca a persona
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS entrega_beca (
    id                 BIGSERIAL PRIMARY KEY,
    evento_id          INTEGER     NOT NULL,
    persona_id         INTEGER     NULL,         -- FK persona.id (resuelta por cédula)
    proyecto_codigo    TEXT        NOT NULL DEFAULT '0002377',
    convenio_codigo    VARCHAR(40) NOT NULL DEFAULT '773-2025',
    -- Trazabilidad denormalizada de meta(s) — CSV '23771,23772' si cumple ambas.
    metas_codigos      VARCHAR(40) NULL,

    -- Datos denormalizados de la persona (flujo público sin login).
    -- Nombres separados para alimentar `persona.{nombre1,nombre2,apellido1,apellido2}`
    -- vía obtener_o_crear_persona() (política A — si la cédula existe no se sobrescribe).
    tipo_doc_codigo    INTEGER     NULL,
    numero_documento   VARCHAR(40) NOT NULL,
    nombre1            VARCHAR(80) NOT NULL,
    nombre2            VARCHAR(80) NULL,
    apellido1          VARCHAR(80) NOT NULL,
    apellido2          VARCHAR(80) NULL,
    telefono           VARCHAR(40) NULL,
    correo             VARCHAR(120) NULL,

    -- Ubicación
    direccion          TEXT        NULL,
    barrio_codigo      VARCHAR(10) NULL,
    upz_codigo         VARCHAR(10) NULL,
    upl_codigo         SMALLINT    NULL,

    -- Cumplimiento metas (23771 acceso + 23772 permanencia)
    cumplimiento_acceso      BOOLEAN NOT NULL DEFAULT FALSE,
    cumplimiento_permanencia BOOLEAN NOT NULL DEFAULT FALSE,
    nivel_formacion          VARCHAR(40) NULL,    -- tecnico_profesional / tecnologo / profesional / etdh
    institucion              TEXT        NULL,
    programa_academico       TEXT        NULL,
    periodo_academico        VARCHAR(20) NULL,

    -- Firma del beneficiario
    firma_imagen_url    TEXT          NULL,
    firma_mongo_id      VARCHAR(64)   NULL,
    firma_fecha         DATE          NULL,

    -- Estado + auditoría
    estado     VARCHAR(20)  NOT NULL DEFAULT 'enviada',  -- enviada / validada / rechazada
    observaciones TEXT      NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_entrega_beca_estado CHECK (estado IN ('enviada','validada','rechazada'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_entrega_beca_evento_doc
  ON entrega_beca (evento_id, numero_documento);
CREATE INDEX IF NOT EXISTS idx_entrega_beca_evento  ON entrega_beca (evento_id);
CREATE INDEX IF NOT EXISTS idx_entrega_beca_persona ON entrega_beca (persona_id);
CREATE INDEX IF NOT EXISTS idx_entrega_beca_estado  ON entrega_beca (estado);
CREATE INDEX IF NOT EXISTS idx_entrega_beca_created ON entrega_beca (created_at DESC);

ALTER TABLE entrega_beca
  ADD CONSTRAINT fk_entrega_beca_evento FOREIGN KEY (evento_id)
  REFERENCES evento (id) ON DELETE RESTRICT;
ALTER TABLE entrega_beca
  ADD CONSTRAINT fk_entrega_beca_persona FOREIGN KEY (persona_id)
  REFERENCES persona (id) ON DELETE SET NULL;

COMMENT ON TABLE entrega_beca IS
  'Registro de entrega de beca a un estudiante (convenio 773-2025, '
  'metas 23771 acceso / 23772 permanencia). Una fila = un acta de '
  'entrega. UNIQUE(evento_id, numero_documento) evita duplicados.';

-- Puente M2M con elementos entregados
CREATE TABLE IF NOT EXISTS entrega_beca_elemento (
    entrega_id       BIGINT   NOT NULL REFERENCES entrega_beca     (id) ON DELETE CASCADE,
    elemento_codigo  SMALLINT NOT NULL REFERENCES elemento_dotacion (codigo) ON DELETE RESTRICT,
    cantidad         INTEGER  NOT NULL DEFAULT 1,
    PRIMARY KEY (entrega_id, elemento_codigo)
);

-- ─────────────────────────────────────────────────────────────────────
-- 3. Tipo de evento del módulo (un solo tipo — el otro reusa ENTREGA)
-- ─────────────────────────────────────────────────────────────────────
INSERT INTO tipo_evento (codigo, nombre, descripcion, activo,
                         permite_inscripcion, permite_caracterizacion,
                         permite_qr, requiere_actividad_plan)
VALUES
    ('JOVENES_BECA',
     'Jóvenes a la E — Entrega de beca',
     'Captura por QR: registro de beneficiario de beca (convenio 773-2025, metas 23771 acceso / 23772 permanencia).',
     TRUE, TRUE, FALSE, TRUE, FALSE)
ON CONFLICT (codigo) DO NOTHING;

COMMIT;

-- ============================================================================
-- VERIFICACIÓN POSTERIOR
-- ============================================================================
-- \d+ elemento_dotacion
-- \d+ entrega_beca
-- \d+ entrega_beca_elemento
-- SELECT codigo, nombre, activo FROM tipo_evento WHERE codigo = 'JOVENES_BECA';
-- SELECT count(*) FROM elemento_dotacion;  -- esperar 5

-- ============================================================================
-- SCRIPT DE REVERSA
-- ============================================================================
-- BEGIN;
-- DROP TABLE IF EXISTS entrega_beca_elemento;
-- DROP TABLE IF EXISTS entrega_beca;
-- DROP TABLE IF EXISTS elemento_dotacion;
-- DELETE FROM tipo_evento WHERE codigo = 'JOVENES_BECA';
-- COMMIT;
