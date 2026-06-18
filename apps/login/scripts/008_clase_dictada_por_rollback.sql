-- 008_clase_dictada_por_rollback.sql
-- Revierte 008_clase_dictada_por.sql.

DROP INDEX IF EXISTS idx_clase_dictada_por;

ALTER TABLE clase DROP CONSTRAINT IF EXISTS fk_clase_dictada_por;

ALTER TABLE clase DROP COLUMN IF EXISTS dictada_por_id;
