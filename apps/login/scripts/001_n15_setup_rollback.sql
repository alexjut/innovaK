-- Rollback de N15 PR-1. OJO: si ya hay datos en rol_modulo o rol_meta,
-- este rollback los pierde. Usar solo si el setup falla.
BEGIN;
DROP TABLE IF EXISTS rol_modulo CASCADE;
DROP TABLE IF EXISTS rol_meta CASCADE;
DROP TABLE IF EXISTS modulo CASCADE;
UPDATE auth_group SET name = 'lider participacion' WHERE name = 'LiderParticipacion';
COMMIT;
