-- 004_contratos_infraestructura_rollback.sql — revierte 004_contratos_infraestructura.sql

BEGIN;

DROP TABLE IF EXISTS intervencion_parque;
DROP TABLE IF EXISTS tramo_vial_contrato;

ALTER TABLE contrato DROP COLUMN IF EXISTS categoria;
ALTER TABLE contrato DROP COLUMN IF EXISTS proyecto_codigo;
ALTER TABLE contrato DROP COLUMN IF EXISTS proyecto_nombre;
ALTER TABLE contrato DROP COLUMN IF EXISTS ejecucion;
ALTER TABLE contrato DROP COLUMN IF EXISTS interventoria_contrato;
ALTER TABLE contrato DROP COLUMN IF EXISTS interventoria_valor;

COMMIT;
