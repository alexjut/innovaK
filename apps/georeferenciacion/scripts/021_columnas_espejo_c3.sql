-- 021 — C3: columnas espejo uniformes en las tablas de fuentes oficiales.
--
-- Toda tabla que es espejo de una fuente externa debería poder responder lo
-- mismo sin que haya que recordar cómo la escribió su comando: cuándo se
-- sincronizó (`synced_at`), de dónde salió (`fuente`), si la fila cambió
-- respecto a la corrida anterior (`hash_fila`) y a qué corte de la fuente
-- corresponde (`fecha_fuente`). Hoy cada tabla tiene un subconjunto distinto:
--
--     tabla                synced_at  fuente  hash_fila  fecha_fuente   filas
--     colegio_sede             sí       sí       FALTA      FALTA          79
--     cai                      sí       sí       FALTA      FALTA          15
--     manzana_estrato        FALTA    FALTA      FALTA        sí       18.929
--     placa_domiciliaria       sí     FALTA      FALTA      FALTA    1.771.088
--     sector_catastral       FALTA    FALTA      FALTA        sí        1.230
--     barrio_legalizado      FALTA    FALTA      FALTA        sí        1.709
--
-- Este script agrega SOLO lo que falta. Es puramente aditivo:
--
--   * Todas las columnas son NULLABLE y sin DEFAULT. En PostgreSQL 11+ eso es
--     un cambio de metadatos: no reescribe la tabla ni toma lock largo. Se
--     verificó que el servidor es **PostgreSQL 16.14** antes de correrlo, que
--     es lo que hace seguro tocar `placa_domiciliaria` con sus 1,77 M de filas.
--   * `IF NOT EXISTS` en cada ADD: correrlo dos veces no falla.
--   * Ninguna fila existente se toca. Las columnas nuevas quedan NULL hasta
--     que el sync correspondiente vuelva a correr con --write, que es
--     exactamente lo que queremos: NULL significa "esta fila viene de antes de
--     que midiéramos esto", y no una fecha inventada.
--
-- `fecha_fuente` NO se agrega donde no está (colegio_sede, cai,
-- placa_domiciliaria): esas fuentes ya traen su corte en otra columna
-- (`fecha_corte` en colegio_sede y cai) y renombrarla rompería las vistas que
-- la leen. Ver la nota de C3 en docs/RUMBO.md.
--
-- Rollback: 021_columnas_espejo_c3_rollback.sql
-- Aplicado el 2026-08-06 sobre poblacion_kennedy (backup diario de las 02:00).

BEGIN;

-- ── Las que ya tienen synced_at y fuente: solo les falta el hash ──────────
ALTER TABLE colegio_sede       ADD COLUMN IF NOT EXISTS hash_fila    text;
ALTER TABLE cai                ADD COLUMN IF NOT EXISTS hash_fila    text;

-- ── placa_domiciliaria: tiene synced_at; le faltan fuente y hash ─────────
ALTER TABLE placa_domiciliaria ADD COLUMN IF NOT EXISTS fuente       varchar(20);
ALTER TABLE placa_domiciliaria ADD COLUMN IF NOT EXISTS hash_fila    text;

-- ── Las tres capas de territorio: solo tienen fecha_fuente ───────────────
ALTER TABLE manzana_estrato    ADD COLUMN IF NOT EXISTS synced_at    timestamptz;
ALTER TABLE manzana_estrato    ADD COLUMN IF NOT EXISTS fuente       varchar(20);
ALTER TABLE manzana_estrato    ADD COLUMN IF NOT EXISTS hash_fila    text;

ALTER TABLE sector_catastral   ADD COLUMN IF NOT EXISTS synced_at    timestamptz;
ALTER TABLE sector_catastral   ADD COLUMN IF NOT EXISTS fuente       varchar(20);
ALTER TABLE sector_catastral   ADD COLUMN IF NOT EXISTS hash_fila    text;

ALTER TABLE barrio_legalizado  ADD COLUMN IF NOT EXISTS synced_at    timestamptz;
ALTER TABLE barrio_legalizado  ADD COLUMN IF NOT EXISTS fuente       varchar(20);
ALTER TABLE barrio_legalizado  ADD COLUMN IF NOT EXISTS hash_fila    text;

COMMIT;
