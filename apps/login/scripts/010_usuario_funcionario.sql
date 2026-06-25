-- =====================================================================
-- RBAC con alcance — PR-1: vínculo de identidad usuario → funcionario
-- Es el cimiento del scope por subgrupo: el subgrupo de un usuario sale
-- de funcionario.subgrupo_id. Antes NO existía ningún vínculo (el código
-- leía usuario.persona_id que no existe → scope era no-op permisivo).
--
-- Columna NULLABLE: un usuario sin funcionario (admins transversales,
-- cuentas de servicio) queda NULL = comportamiento actual (sin scope).
-- NO cambia ningún comportamiento por sí sola; el filtrado llega en PR-4.
--
-- APLICAR tras backup < 24 h (hay poblacion_kennedy_diario.dump de hoy).
-- Sin psql en el contenedor:
--   connection.cursor().execute(open('.../010_usuario_funcionario.sql').read())
-- =====================================================================
BEGIN;

ALTER TABLE usuario ADD COLUMN IF NOT EXISTS funcionario_id INTEGER
  REFERENCES funcionario(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_usuario_funcionario ON usuario(funcionario_id);

COMMIT;
