-- =====================================================================
-- RBAC con alcance — PR-6: auditoría de asignación/cambio de rol (Ley 1581)
-- Deja rastro de quién asignó/quitó qué rol/subgrupo a quién y cuándo.
--
-- APLICAR tras backup < 24 h. Sin psql en el contenedor:
--   connection.cursor().execute(open('.../012_auditoria_pertenencia.sql').read())
-- =====================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS auditoria_pertenencia (
    id BIGSERIAL PRIMARY KEY,
    usuario_objetivo_id INTEGER REFERENCES usuario(id) ON DELETE SET NULL,
    actor_id INTEGER REFERENCES usuario(id) ON DELETE SET NULL,
    accion VARCHAR(40) NOT NULL,        -- asignar_rol | quitar_rol | asignar_subgrupo | vincular_funcionario
    group_id INTEGER REFERENCES auth_group(id) ON DELETE SET NULL,
    objetivo_tipo VARCHAR(20),
    objetivo_id BIGINT,
    detalle TEXT,
    ts TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_auditoria_objetivo ON auditoria_pertenencia(usuario_objetivo_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_ts       ON auditoria_pertenencia(ts);

COMMIT;

-- REVERSA:  DROP TABLE IF EXISTS auditoria_pertenencia;
