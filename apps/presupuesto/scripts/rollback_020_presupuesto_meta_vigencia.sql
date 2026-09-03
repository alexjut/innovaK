-- Rollback del 020. La tabla es nueva y nada más la referencia: basta el DROP.
BEGIN;
DROP TABLE IF EXISTS presu_presupuesto_meta_vigencia;
COMMIT;
