-- ============================================================================
-- N12 — Setup wizards de caracterización
-- ============================================================================
--
-- Bloque DDL idempotente que prepara la BD para la app `caracterizacion`.
--
-- Cambios:
--   1. evento.sector_caracterizacion VARCHAR(20) NULL          (selector de wizard)
--   2. 5 secuencias BIGSERIAL para caracterizacion_*           (cierra deuda S5 del módulo)
--   3. DROP UNIQUE(persona_id) en 5 tablas                     (permite re-caracterizar)
--   4. ADD evento_id en salud / poblacional / participación    (trazabilidad)
--   5. ADD firma_mongo_id en caracterizacion_salud             (firma cifrada en Mongo)
--   6. ALTER caracterizacion_cultura.persona_id NOT NULL       (consistencia con resto)
--
-- Pre-requisitos:
--   - Backup pre-N12 ejecutado (poblacion_kennedy_pre_n12_*.dump)
--   - Las 6 tablas caracterizacion_* están vacías (verificado 2026-04-30)
--
-- Ejecución:
--   docker exec -i innova_postgres psql -U innova-bd -d poblacion_kennedy < 001_n12_setup.sql
--   (o adaptar al host donde corra postgres si no está dockerizado)
--
-- Reversión: ver 001_n12_setup_rollback.sql
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1) Selector de sector en evento
-- ----------------------------------------------------------------------------
ALTER TABLE evento
    ADD COLUMN IF NOT EXISTS sector_caracterizacion VARCHAR(20) NULL;

COMMENT ON COLUMN evento.sector_caracterizacion IS
    'Sector del wizard de caracterización (cultura|deporte|mujer|salud|poblacional|participacion_ciudadana). NULL = evento de otro tipo o legacy sin sector asignado.';

-- ----------------------------------------------------------------------------
-- 2) Secuencias BIGSERIAL para 5 tablas (la 6a, participacion_ciudadana, ya tiene)
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    t TEXT;
    seq_name TEXT;
BEGIN
    FOR t IN SELECT unnest(ARRAY[
        'caracterizacion_cultura',
        'caracterizacion_deporte',
        'caracterizacion_mujer',
        'caracterizacion_salud',
        'caracterizacion_poblacional'
    ]) LOOP
        seq_name := t || '_id_seq';
        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = seq_name AND relkind = 'S') THEN
            EXECUTE format('CREATE SEQUENCE %I OWNED BY %I.id', seq_name, t);
            EXECUTE format('ALTER TABLE %I ALTER COLUMN id SET DEFAULT nextval(%L)', t, seq_name);
            EXECUTE format('SELECT setval(%L, COALESCE((SELECT MAX(id) FROM %I), 0) + 1, false)', seq_name, t);
            RAISE NOTICE 'Creada secuencia % para tabla %', seq_name, t;
        ELSE
            RAISE NOTICE 'Secuencia % ya existe, se omite', seq_name;
        END IF;
    END LOOP;
END $$;

-- ----------------------------------------------------------------------------
-- 3) Eliminar UNIQUE(persona_id) — una persona puede caracterizarse en eventos distintos
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    t TEXT;
    cons_name TEXT;
BEGIN
    FOR t IN SELECT unnest(ARRAY[
        'caracterizacion_cultura',
        'caracterizacion_deporte',
        'caracterizacion_mujer',
        'caracterizacion_salud',
        'caracterizacion_poblacional'
    ]) LOOP
        SELECT conname INTO cons_name
        FROM pg_constraint c
        JOIN pg_class cl ON cl.oid = c.conrelid
        WHERE cl.relname = t
          AND c.contype = 'u'
          AND EXISTS (
              SELECT 1
              FROM pg_attribute a
              WHERE a.attrelid = cl.oid
                AND a.attname = 'persona_id'
                AND a.attnum = ANY(c.conkey)
          )
          AND array_length(c.conkey, 1) = 1
        LIMIT 1;

        IF cons_name IS NOT NULL THEN
            EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', t, cons_name);
            RAISE NOTICE 'Eliminado UNIQUE % en tabla %', cons_name, t;
        ELSE
            RAISE NOTICE 'Sin UNIQUE(persona_id) en tabla %, se omite', t;
        END IF;
    END LOOP;
END $$;

-- ----------------------------------------------------------------------------
-- 4) Agregar evento_id donde falta + índice
-- ----------------------------------------------------------------------------
ALTER TABLE caracterizacion_salud
    ADD COLUMN IF NOT EXISTS evento_id INTEGER NULL REFERENCES evento(id);
ALTER TABLE caracterizacion_poblacional
    ADD COLUMN IF NOT EXISTS evento_id INTEGER NULL REFERENCES evento(id);
ALTER TABLE caracterizacion_participacion_ciudadana
    ADD COLUMN IF NOT EXISTS evento_id INTEGER NULL REFERENCES evento(id);

CREATE INDEX IF NOT EXISTS idx_carac_salud_evento
    ON caracterizacion_salud(evento_id);
CREATE INDEX IF NOT EXISTS idx_carac_poblacional_evento
    ON caracterizacion_poblacional(evento_id);
CREATE INDEX IF NOT EXISTS idx_carac_partciud_evento
    ON caracterizacion_participacion_ciudadana(evento_id);

-- ----------------------------------------------------------------------------
-- 5) Firma cifrada en Mongo para sector salud
-- ----------------------------------------------------------------------------
ALTER TABLE caracterizacion_salud
    ADD COLUMN IF NOT EXISTS firma_mongo_id VARCHAR(64) NULL;

COMMENT ON COLUMN caracterizacion_salud.firma_mongo_id IS
    'ObjectId del documento Mongo que guarda la firma cifrada (AES-256-GCM). NULL si no hay firma cargada.';

-- ----------------------------------------------------------------------------
-- 6) Consistencia: caracterizacion_cultura.persona_id pasa a NOT NULL
--    (las otras 4 ya lo son; segura porque la tabla está vacía)
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'caracterizacion_cultura'
          AND column_name = 'persona_id'
          AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE caracterizacion_cultura ALTER COLUMN persona_id SET NOT NULL;
        RAISE NOTICE 'persona_id en caracterizacion_cultura ahora es NOT NULL';
    END IF;
END $$;

COMMIT;

-- ----------------------------------------------------------------------------
-- Verificación post-DDL (corre con \i o copia/pega)
-- ----------------------------------------------------------------------------
-- SELECT column_name FROM information_schema.columns
--  WHERE table_name='evento' AND column_name='sector_caracterizacion';
--
-- SELECT relname FROM pg_class WHERE relkind='S' AND relname LIKE 'caracterizacion_%_id_seq';
--
-- SELECT conrelid::regclass, conname FROM pg_constraint
--  WHERE contype='u' AND conrelid::regclass::text LIKE 'caracterizacion_%';
--
-- SELECT table_name, column_name FROM information_schema.columns
--  WHERE table_name LIKE 'caracterizacion_%' AND column_name='evento_id'
--  ORDER BY table_name;
--
-- SELECT column_name, is_nullable FROM information_schema.columns
--  WHERE table_name='caracterizacion_salud' AND column_name IN ('firma_mongo_id','firma_digital');
