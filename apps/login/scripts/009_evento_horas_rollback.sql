-- 009_evento_horas_rollback.sql — revierte 009_evento_horas.sql

BEGIN;

ALTER TABLE evento      DROP COLUMN IF EXISTS hora_inicio;
ALTER TABLE evento      DROP COLUMN IF EXISTS hora_fin;
ALTER TABLE tipo_evento DROP COLUMN IF EXISTS requiere_horario;

COMMIT;
