-- C3 (2026-08-05) — unifica el nombre de la columna "cuándo lo sincronizamos"
-- a `synced_at` en toda tabla espejo.
--
-- Hoy conviven tres nombres para lo mismo: `ingerido_en` (sdp_meta_oficial,
-- secop_contrato) y `sincronizado_at` (placa_domiciliaria). El objetivo de C3
-- es "las mismas cuatro columnas (fuente, fecha_fuente, synced_at, hash_fila)
-- en toda tabla espejo" (RUMBO). Este script hace la parte de `synced_at`.
--
-- SOLO RENOMBRA columnas que ya existen y ya se escriben — no borra ni agrega
-- datos. En Postgres, RENAME COLUMN es una operación de METADATOS: instantánea,
-- incluso en placa_domiciliaria (1,77 M filas).
--
-- Los ÚNICOS lectores/escritores de estos nombres son 2 modelos (db_column) y
-- 3 comandos (SQL crudo), verificado con grep; se actualizan en el MISMO commit:
--   apps/presupuesto/models/sdp_oficial.py, secop.py
--   apps/presupuesto/management/commands/ingest_sdp_datos_abiertos.py, ingest_secop_contratos.py
--   apps/georeferenciacion/management/commands/sync_placas.py
-- `fecha_corte` (cai, colegio_sede) NO se toca: lo leen muchas vistas y ES, por
-- convención, la "fecha de la fuente" de esas tablas.
--
-- Backup previo verificado: poblacion_kennedy_diario.dump (hoy 02:00, < 24 h).

BEGIN;

ALTER TABLE sdp_meta_oficial   RENAME COLUMN ingerido_en     TO synced_at;
ALTER TABLE secop_contrato     RENAME COLUMN ingerido_en     TO synced_at;
ALTER TABLE placa_domiciliaria RENAME COLUMN sincronizado_at TO synced_at;

COMMIT;

-- ── ROLLBACK (si algo sale mal) ──────────────────────────────────────────
-- BEGIN;
-- ALTER TABLE sdp_meta_oficial   RENAME COLUMN synced_at TO ingerido_en;
-- ALTER TABLE secop_contrato     RENAME COLUMN synced_at TO ingerido_en;
-- ALTER TABLE placa_domiciliaria RENAME COLUMN synced_at TO sincronizado_at;
-- COMMIT;
