-- rollback_017_etapa_orden_unico.sql — quita la restricción de orden único.
--
-- Sin riesgo: quitar un UNIQUE no toca datos. Vuelve a permitir dos etapas en
-- el mismo puesto del stepper, con el efecto descrito en el 017.

BEGIN;
ALTER TABLE etapa_contrato DROP CONSTRAINT IF EXISTS etapa_contrato_orden_key;
COMMIT;
