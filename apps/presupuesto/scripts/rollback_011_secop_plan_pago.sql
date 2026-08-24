-- REVERSA de 011_secop_plan_pago.sql.
-- La tabla es un ESPEJO: todo su contenido se vuelve a bajar con
-- `manage.py ingest_secop_plan_pagos --write`, así que borrarla no pierde
-- ningún dato que la Alcaldía haya capturado. Nada más depende de ella:
-- el expediente la lee con `to_regclass` y, si no está, publica el plan de
-- pago vacío con su motivo (no revienta).
BEGIN;
DROP TABLE IF EXISTS secop_plan_pago;
COMMIT;
