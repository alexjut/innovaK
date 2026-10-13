-- Reversión del 032. La tabla es un ESPEJO: nada de lo que guarda es original,
-- todo se puede volver a traer con `ingest_secop_suspensiones`. Por eso se
-- puede borrar sin ceremonia, al contrario de una tabla con captura propia.
BEGIN;
DROP TABLE IF EXISTS secop_suspension;
COMMIT;
