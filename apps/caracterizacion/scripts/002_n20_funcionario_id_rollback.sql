-- Rollback de 002_n20_funcionario_id.sql
-- Solo correr si hay que revertir N20 y aún no se ha poblado datos en
-- la columna `funcionario_id` (DROP es destructivo).

BEGIN;

DROP INDEX IF EXISTS idx_caract_cultura_funcionario;
DROP INDEX IF EXISTS idx_caract_deporte_funcionario;
DROP INDEX IF EXISTS idx_caract_mujer_funcionario;
DROP INDEX IF EXISTS idx_caract_salud_funcionario;
DROP INDEX IF EXISTS idx_caract_poblacional_funcionario;
DROP INDEX IF EXISTS idx_caract_participacion_funcionario;

ALTER TABLE caracterizacion_cultura DROP COLUMN IF EXISTS funcionario_id;
ALTER TABLE caracterizacion_deporte DROP COLUMN IF EXISTS funcionario_id;
ALTER TABLE caracterizacion_mujer DROP COLUMN IF EXISTS funcionario_id;
ALTER TABLE caracterizacion_salud DROP COLUMN IF EXISTS funcionario_id;
ALTER TABLE caracterizacion_poblacional DROP COLUMN IF EXISTS funcionario_id;
ALTER TABLE caracterizacion_participacion_ciudadana DROP COLUMN IF EXISTS funcionario_id;

COMMIT;
