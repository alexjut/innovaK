-- rollback_014_contrato_plan_pago.sql — deshace 014.
--
-- OJO: BORRA los planes de pago que hayan capturado las áreas. Como esta tabla
-- NO replica a SECOP, lo que hay acá no está en ninguna otra parte.
-- Exportarlo antes:
--   \copy contrato_plan_pago TO 'planes.csv' CSV HEADER

BEGIN;

DROP TABLE IF EXISTS contrato_plan_pago;

COMMIT;
