-- =====================================================================
-- RBAC con alcance — PR-2: tabla de pertenencia con scope
-- Reemplaza la pertenencia plana usuario↔grupo por una con ALCANCE:
--   (usuario, rol/grupo, objetivo_tipo, objetivo_id)
-- objetivo_tipo: 'global' | 'subgrupo' | 'contrato' | 'curso'
-- objetivo_id: id del subgrupo/contrato/curso; 0 para 'global' (sin scope).
--
-- En PR-2 se POBLA solo con filas 'global' espejo de usuario_grupos →
-- CERO cambio de comportamiento. PR-3 hace que el cálculo de módulos lea
-- de aquí; PR-4 aplica el filtrado por subgrupo.
--
-- APLICAR tras backup < 24 h. Sin psql en el contenedor:
--   connection.cursor().execute(open('.../011_usuario_pertenencia.sql').read())
-- =====================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS usuario_pertenencia (
    id BIGSERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    group_id   INTEGER NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
    objetivo_tipo VARCHAR(20) NOT NULL DEFAULT 'global',
    objetivo_id BIGINT NOT NULL DEFAULT 0,   -- 0 = global (sin scope)
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by_id INTEGER REFERENCES usuario(id) ON DELETE SET NULL,
    CONSTRAINT ck_pertenencia_tipo
      CHECK (objetivo_tipo IN ('global','subgrupo','contrato','curso')),
    CONSTRAINT uq_usuario_pertenencia
      UNIQUE (usuario_id, group_id, objetivo_tipo, objetivo_id)
);
CREATE INDEX IF NOT EXISTS idx_pertenencia_usuario ON usuario_pertenencia(usuario_id);
CREATE INDEX IF NOT EXISTS idx_pertenencia_group   ON usuario_pertenencia(group_id);
CREATE INDEX IF NOT EXISTS idx_pertenencia_scope   ON usuario_pertenencia(objetivo_tipo, objetivo_id);

COMMIT;

-- =====================================================================
-- REVERSA:  DROP TABLE IF EXISTS usuario_pertenencia;
-- =====================================================================
