-- ============================================================================
-- N15 (hotfix) — Limpieza + UNIQUE en usuario_grupos
-- ============================================================================
--
-- Detectado en sesión 2026-04-30: la tabla `usuario_grupos` (M2M
-- User.groups, db_table custom del modelo Usuario en innovaK) NO tenía
-- constraint UNIQUE(usuario_id, group_id). Resultado: el usuario
-- alexjut tenía 3 filas duplicadas para el grupo Admin, lo que se veía
-- en la UI de roles como "alexjut" repetido 3 veces.
--
-- Este script:
--   1. Borra duplicados conservando la fila con id mínimo por par.
--   2. Agrega el constraint UNIQUE para prevenir futuros duplicados.
--
-- Idempotente: el DELETE no toca nada si ya está limpio; el ADD
-- CONSTRAINT falla la 2da vez con "already exists" (envolver en bloque
-- IF NOT EXISTS para seguridad).
-- ============================================================================

BEGIN;

-- 1. Limpieza de duplicados
DELETE FROM usuario_grupos
WHERE id IN (
    SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (
            PARTITION BY usuario_id, group_id ORDER BY id
        ) AS rn
        FROM usuario_grupos
    ) t
    WHERE t.rn > 1
);

-- 2. Constraint UNIQUE (idempotente)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'usuario_grupos_usuario_group_uniq'
    ) THEN
        ALTER TABLE usuario_grupos
            ADD CONSTRAINT usuario_grupos_usuario_group_uniq
            UNIQUE (usuario_id, group_id);
    END IF;
END $$;

COMMIT;
