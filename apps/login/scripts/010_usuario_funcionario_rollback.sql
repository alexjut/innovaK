-- Rollback PR-1 RBAC — quita el vínculo usuario → funcionario.
BEGIN;
DROP INDEX IF EXISTS idx_usuario_funcionario;
ALTER TABLE usuario DROP COLUMN IF EXISTS funcionario_id;
COMMIT;
