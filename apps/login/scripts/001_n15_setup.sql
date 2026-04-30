-- ============================================================================
-- N15 PR-1 — Setup de tablas para administración de roles dinámico
-- ============================================================================
--
-- Crea 3 tablas nuevas (no toca auth_*):
--   1. modulo                  — catálogo de módulos del sistema
--   2. rol_modulo              — M2M auth_group ↔ modulo
--   3. rol_meta                — atributos extendidos del rol (1:1 con auth_group)
--
-- Renombra el grupo 'lider participacion' → 'LiderParticipacion'.
-- Siembra rol_meta para los 7 grupos existentes (Admin protegido).
--
-- Pre-requisitos:
--   - Backup pre-N15 ejecutado
--   - Decisiones aprobadas: 1a (15 módulos), 2a (bypass superuser),
--     3b (granular kactivo en PR-5), 4a (solo Admin protegido), 5a (rename)
--
-- El catálogo `modulo` y la asignación `rol_modulo` los puebla un
-- management command idempotente (`python manage.py seed_modulos`).
-- Eso permite re-correrlo y versionar los módulos en el repo.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1) Catálogo de módulos
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS modulo (
    codigo        VARCHAR(50)  PRIMARY KEY,
    nombre        VARCHAR(100) NOT NULL,
    descripcion   TEXT         NULL,
    icono         VARCHAR(50)  NULL,
    orden         SMALLINT     NOT NULL DEFAULT 100,
    activo        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_modulo_activo_orden ON modulo (activo, orden);

COMMENT ON TABLE modulo IS
    'Catálogo de módulos del sistema. Cada decorador @modulo_required(codigo) lo referencia. PK semántica para resistir renames de orden.';

-- ----------------------------------------------------------------------------
-- 2) Asociación rol ↔ módulo (M2M)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rol_modulo (
    id              BIGSERIAL PRIMARY KEY,
    group_id        INTEGER     NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
    modulo_codigo   VARCHAR(50) NOT NULL REFERENCES modulo(codigo) ON DELETE CASCADE,
    created_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (group_id, modulo_codigo)
);
CREATE INDEX IF NOT EXISTS idx_rol_modulo_group  ON rol_modulo (group_id);
CREATE INDEX IF NOT EXISTS idx_rol_modulo_codigo ON rol_modulo (modulo_codigo);

COMMENT ON TABLE rol_modulo IS
    'M2M entre auth_group y modulo. Marcar/desmarcar checkbox en la UI inserta/borra fila aquí.';

-- ----------------------------------------------------------------------------
-- 3) Metadatos extendidos del rol (1:1 con auth_group)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rol_meta (
    group_id      INTEGER PRIMARY KEY REFERENCES auth_group(id) ON DELETE CASCADE,
    descripcion   TEXT       NULL,
    activo        BOOLEAN    NOT NULL DEFAULT TRUE,
    es_protegido  BOOLEAN    NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMP  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON COLUMN rol_meta.es_protegido IS
    'TRUE = no se puede borrar ni desactivar (Admin). Backend rechaza también desmarcar el módulo "roles" de un rol protegido.';

-- ----------------------------------------------------------------------------
-- 4) Renombrar grupo "lider participacion" → "LiderParticipacion"
-- ----------------------------------------------------------------------------
UPDATE auth_group
SET name = 'LiderParticipacion'
WHERE name = 'lider participacion';

-- ----------------------------------------------------------------------------
-- 5) Sembrar rol_meta para los grupos existentes
--    (Admin protegido; el resto editable). Idempotente con ON CONFLICT.
-- ----------------------------------------------------------------------------
INSERT INTO rol_meta (group_id, descripcion, activo, es_protegido)
SELECT id,
    CASE name
        WHEN 'Admin'                THEN 'Acceso total al sistema'
        WHEN 'Lider'                THEN 'Líder de proceso (presupuesto + actividades)'
        WHEN 'Coordinador'          THEN 'Coordinador de cursos kactivo'
        WHEN 'Docente'              THEN 'Docente con acceso a asistencia'
        WHEN 'LiderParticipacion'   THEN 'Líder de participación ciudadana'
        WHEN 'UsuarioGeneral'       THEN 'Consulta general'
        WHEN 'CoordinadorDeportes'  THEN 'Coordinador del subgrupo Deportes'
        ELSE name
    END,
    TRUE,
    (name = 'Admin')
FROM auth_group
ON CONFLICT (group_id) DO NOTHING;

COMMIT;

-- ----------------------------------------------------------------------------
-- Verificación post-DDL
-- ----------------------------------------------------------------------------
-- SELECT count(*) FROM rol_meta;            -- debería ser 7
-- SELECT name FROM auth_group ORDER BY name;-- 'LiderParticipacion' presente
-- SELECT count(*) FROM modulo;              -- 0 (lo siembra el management command)
-- SELECT count(*) FROM rol_modulo;          -- 0 (idem)
