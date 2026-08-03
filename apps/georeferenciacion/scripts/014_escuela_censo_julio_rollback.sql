-- ============================================================================
-- Rollback de 014_escuela_censo_julio.sql
--
-- Revierte TODO lo que agregó el 014: los índices, las constraints y las
-- columnas, en orden inverso. Después de correrlo, `escuela` queda con las 13
-- columnas originales y sin rastro del 014.
--
-- ⚠️ LEER ANTES DE CORRER
--   Si el censo de julio YA se cargó, esto borra:
--     · qué escuelas se dieron de baja y por qué (estado/motivo_baja/fecha_baja)
--     · la dirección de abril que se guardó al sobrescribir
--       (direccion_anterior) — y en 6 casos esa es la ÚNICA dirección que
--       existe, porque la de julio vino vacía;
--     · el barrio resuelto por geometría y las discrepancias detectadas;
--     · las que quedaron marcadas para revisión del área;
--     · actividades, horarios, edades y formador del popup.
--
--   Antes de correrlo:
--       SELECT count(*) FROM escuela WHERE estado = 'inactivo';
--       SELECT count(*) FROM escuela WHERE direccion_anterior IS NOT NULL;
--       SELECT count(*) FROM escuela WHERE revision_requerida IS TRUE;
--       SELECT count(*) FROM escuela WHERE actividades IS NOT NULL;
--   Si devuelven > 0, saque backup y confirme que se puede perder.
--
--   Las FILAS cargadas por el censo NO se borran acá: eso es dato, no
--   estructura. Se quitan aparte y mirando qué se cargó:
--       DELETE FROM escuela WHERE origen = 'censo_2026_07';
-- ============================================================================

BEGIN;

-- ── Índices ────────────────────────────────────────────────────────────────
DROP INDEX IF EXISTS idx_escuela_pintables;
DROP INDEX IF EXISTS idx_escuela_upz_res;
DROP INDEX IF EXISTS idx_escuela_origen;
DROP INDEX IF EXISTS idx_escuela_estado;

-- ── Constraints ────────────────────────────────────────────────────────────
ALTER TABLE escuela DROP CONSTRAINT IF EXISTS ck_escuela_barrio_estado;
ALTER TABLE escuela DROP CONSTRAINT IF EXISTS ck_escuela_baja_justificada;
ALTER TABLE escuela DROP CONSTRAINT IF EXISTS ck_escuela_estado;

-- ── Columnas ───────────────────────────────────────────────────────────────
ALTER TABLE escuela
    DROP COLUMN IF EXISTS censo_origen,
    DROP COLUMN IF EXISTS url_maps,
    DROP COLUMN IF EXISTS actividades,
    DROP COLUMN IF EXISTS revision_detalle,
    DROP COLUMN IF EXISTS revision_requerida,
    DROP COLUMN IF EXISTS geolocalizado,
    DROP COLUMN IF EXISTS discrepancia,
    DROP COLUMN IF EXISTS upz_resuelta,
    DROP COLUMN IF EXISTS barrio_estado,
    DROP COLUMN IF EXISTS barrio_resuelto,
    DROP COLUMN IF EXISTS barrio_declarado,
    DROP COLUMN IF EXISTS direccion_anterior,
    DROP COLUMN IF EXISTS fecha_baja,
    DROP COLUMN IF EXISTS motivo_baja,
    DROP COLUMN IF EXISTS estado;

COMMIT;
