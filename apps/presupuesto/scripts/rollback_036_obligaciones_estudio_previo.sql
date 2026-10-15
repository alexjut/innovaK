-- Rollback de 036. Borra las obligaciones y el registro de documentos.
--
-- DESTRUCTIVO pero recuperable: los PDF siguen publicados en SECOP y la
-- extracción los vuelve a bajar. Lo que se pierde es el trabajo de extracción
-- —horas de descargas— y el histórico de qué versión del estudio previo se usó
-- para cada certificado emitido. Eso último no se recupera.

BEGIN;

DROP TABLE IF EXISTS secop_obligacion;
DROP TABLE IF EXISTS secop_documento;

COMMIT;
