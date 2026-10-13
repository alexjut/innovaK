-- =====================================================================
-- Agrega programa/objetivo del Plan a la tabla espejo sdp_meta_oficial, para
-- poder mostrar la ESTRUCTURA OFICIAL (Programa → Objetivo → Proyecto → Meta).
-- El dato ya viene en el CSV (ObjetivoPlanDesarrollo, ProgramaPlanDesarrollo);
-- solo faltaba guardarlo. Tras aplicar, re-correr ingest_sdp_datos_abiertos.
--
-- ✅ APLICADO. Comprobado contra la base el 2026-10-13: `sdp_meta_oficial` existe (280 filas).
--
-- El encabezado decía «NO APLICADO» y era falso: fue verdad el día en que se
-- escribió y dejó de serlo al aplicarse. Ese mismo descuido, en
-- specs/004-formulacion/plan.md y 019_formulacion.sql, hizo que en octubre
-- llegara un encargo para construir desde cero un módulo que ya existía: un
-- comentario caduco en el primer archivo que alguien lee cuesta semanas de
-- planificación. Al aplicar un script, se corrige su encabezado en el mismo
-- movimiento.
-- =====================================================================
BEGIN;

ALTER TABLE sdp_meta_oficial ADD COLUMN IF NOT EXISTS codigo_objetivo VARCHAR(20);
ALTER TABLE sdp_meta_oficial ADD COLUMN IF NOT EXISTS objetivo        TEXT;
ALTER TABLE sdp_meta_oficial ADD COLUMN IF NOT EXISTS codigo_programa VARCHAR(20);
ALTER TABLE sdp_meta_oficial ADD COLUMN IF NOT EXISTS programa        TEXT;

CREATE INDEX IF NOT EXISTS idx_sdp_meta_programa ON sdp_meta_oficial (codigo_programa);
CREATE INDEX IF NOT EXISTS idx_sdp_meta_objetivo ON sdp_meta_oficial (codigo_objetivo);

COMMIT;

-- =====================================================================
-- REVERSA:
--   ALTER TABLE sdp_meta_oficial DROP COLUMN IF EXISTS codigo_objetivo;
--   ALTER TABLE sdp_meta_oficial DROP COLUMN IF EXISTS objetivo;
--   ALTER TABLE sdp_meta_oficial DROP COLUMN IF EXISTS codigo_programa;
--   ALTER TABLE sdp_meta_oficial DROP COLUMN IF EXISTS programa;
-- =====================================================================
