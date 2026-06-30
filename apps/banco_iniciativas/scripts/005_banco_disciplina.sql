-- ============================================================================
-- Banco de Iniciativas #62 — Disciplina deportiva (split del doc oficial)
-- Fecha: 2026-06-30 · Rama: feat/banco-qa-#62
--
-- Doc oficial: separar Fútbol / Fútbol sala / Microfútbol, y desglosar
-- "Artes marciales" una por una.
--
-- disciplina_deportiva.codigo = GENERATED ALWAYS AS IDENTITY + UNIQUE(nombre)
-- → mismo patrón que lote 3: OVERRIDING SYSTEM VALUE para códigos explícitos,
--   ON CONFLICT (nombre) DO UPDATE para reusar nombres existentes, y setval()
--   al final para que el próximo alta automática no choque.
--
-- 100% aditivo sobre el catálogo (append + relabel + deactivate). NO toca las
-- inscripciones: las 24 históricas que referencien 'Artes marciales' (cod 5)
-- siguen apuntando a esa fila, que queda inactiva pero RESUELVE para histórico.
-- NO LO CORRE CLAUDE: lo revisa/corre Alex tras snapshot del catálogo.
--
-- ⚠️ ESTADO: aprobado el relabel (Futsala→'Fútbol sala') + alta de Microfútbol.
--    El desglose de ARTES MARCIALES está PENDIENTE de la lista de Deportes
--    (bloque TODO abajo, comentado). Corre el script completo cuando esa lista
--    esté confirmada (y tras snapshot).
-- ============================================================================

BEGIN;

-- ── Aprobado · Fútbol sala: relabel del existente (conserva codigo 1 y refs) ─
-- 'Futsala' (codigo 1) es el mismo concepto que "Fútbol sala" del doc.
-- Solo UPDATE de nombre (UNIQUE(nombre) OK: 'Fútbol sala' no existe aún).
UPDATE disciplina_deportiva SET nombre = 'Fútbol sala' WHERE codigo = 1;

-- ── Aprobado · Microfútbol: alta nueva (faltaba) ────────────────────────────
INSERT INTO disciplina_deportiva (codigo, nombre, activo)
OVERRIDING SYSTEM VALUE VALUES
    (15, 'Microfútbol', TRUE)
ON CONFLICT (nombre) DO UPDATE SET activo = TRUE;

-- ── PENDIENTE · Artes marciales una por una (lista de Deportes) ─────────────
-- Cuando Deportes confirme cuáles ofrece el programa: descomentar, ajustar la
-- lista a la EXACTA, y correr todo junto. Patrón: deactivate-first + alta con
-- OVERRIDING + ON CONFLICT(nombre). Códigos desde 16 (15 = Microfútbol).
-- UPDATE disciplina_deportiva SET activo = FALSE WHERE codigo = 5;  -- 'Artes marciales' (agrupado)
-- INSERT INTO disciplina_deportiva (codigo, nombre, activo)
-- OVERRIDING SYSTEM VALUE VALUES
--     (16, 'Taekwondo',     TRUE),
--     (17, 'Karate-Do',     TRUE),
--     (18, 'Judo',          TRUE),
--     (19, 'Boxeo',         TRUE),
--     (20, 'Lucha',         TRUE),
--     (21, 'Jiu-Jitsu',     TRUE),
--     (22, 'Muay Thai',     TRUE),
--     (23, 'Kickboxing',    TRUE),
--     (24, 'Capoeira',      TRUE),
--     (25, 'Wushu/Kung Fu', TRUE)
-- ON CONFLICT (nombre) DO UPDATE SET activo = TRUE;

-- ── Reset de la secuencia IDENTITY (cubre el MAX final, sea 15 o 25) ────────
SELECT setval('public.disciplina_deportiva_codigo_seq',
              (SELECT MAX(codigo) FROM disciplina_deportiva));

COMMIT;

-- ============================================================================
-- ROLLBACK (best-effort; el relabel de 'Futsala' se restaura desde snapshot).
-- ============================================================================
-- BEGIN;
-- UPDATE disciplina_deportiva SET nombre = 'Futsala' WHERE codigo = 1;
-- DELETE FROM disciplina_deportiva WHERE codigo = 15;            -- Microfútbol
-- -- DELETE FROM disciplina_deportiva WHERE codigo BETWEEN 16 AND 25;  -- artes marciales (si se aplicaron)
-- -- UPDATE disciplina_deportiva SET activo = TRUE WHERE codigo = 5;   -- reactiva 'Artes marciales'
-- SELECT setval('public.disciplina_deportiva_codigo_seq',
--               (SELECT MAX(codigo) FROM disciplina_deportiva));
-- COMMIT;
