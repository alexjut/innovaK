-- ============================================================================
-- Banco de Iniciativas #62 — Catálogo `disciplina_deportiva` (expansión IDRD)
-- Fecha: 2026-06-30 · Rama: feat/banco-qa-#62
--
-- Decisión: el catálogo se EXPANDE al conjunto de disciplinas que se practican
-- en Bogotá (lista oficial IDRD: formación + Escuelas de mi barrio). Reemplaza
-- el alcance previo (solo relabel Futsala + Microfútbol + TODO artes marciales).
--
-- disciplina_deportiva.codigo = GENERATED ALWAYS AS IDENTITY + UNIQUE(nombre)
-- → OVERRIDING SYSTEM VALUE para códigos explícitos, ON CONFLICT (nombre) DO
--   UPDATE SET activo=TRUE (reusa/reactiva si el nombre ya existe), y setval()
--   al final para que el próximo alta automática no choque (lección lote 3).
--
-- 100% aditivo (append + relabel + deactivate). NO toca el histórico: las
-- inscripciones que usen 'Artes marciales' (cod 5, agrupado) lo conservan
-- INACTIVO y siguen resolviendo. Atómico, idempotente, con ROLLBACK.
-- NO LO CORRE CLAUDE: lo revisa/corre Alex tras snapshot del catálogo.
--
-- Gotcha de visibilidad: el form muestra solo activos (exclude(activo=False));
-- el histórico resuelve los inactivos por la relación.
--
-- Conservadas activas SIN tocar (no aparecen abajo): Baloncesto(2), Voleibol(3),
-- Atletismo(4), Patinaje(6), Natación(7), Ajedrez(8), Actividad física para
-- adultos mayores(9), Entrenamiento funcional/Gimnasio(10), Danza/Bailoterapia(11),
-- Ciclismo(12), Otro(13), Fútbol(14).
-- ============================================================================

BEGIN;

-- ── Relabel · Futsala → 'Fútbol sala' (conserva codigo 1 y referencias) ─────
UPDATE disciplina_deportiva SET nombre = 'Fútbol sala' WHERE codigo = 1;

-- ── Relabel · cod 9 → 'Actividad física' (el enfoque etario va en Paso 5) ────
UPDATE disciplina_deportiva SET nombre = 'Actividad física' WHERE codigo = 9;

-- ── Deactivate · 'Artes marciales' agrupado → se reemplaza por individuales ──
UPDATE disciplina_deportiva SET activo = FALSE WHERE codigo = 5;

-- ── Append · disciplinas IDRD (idempotente: ON CONFLICT nombre reactiva) ─────
INSERT INTO disciplina_deportiva (codigo, nombre, activo)
OVERRIDING SYSTEM VALUE VALUES
    -- Conjunto / pelota (cod 15: AMF, ≠ fútbol sala/futsal FIFA del cod 1)
    (15, 'Microfútbol o fútbol de salón', TRUE),
    (16, 'Béisbol',                TRUE),
    (17, 'Sóftbol',                TRUE),
    (18, 'Balonmano',              TRUE),
    (19, 'Rugby',                  TRUE),
    (20, 'Ultimate',               TRUE),
    -- Raqueta
    (21, 'Tenis de campo',         TRUE),
    (22, 'Tenis de mesa',          TRUE),
    (23, 'Bádminton',              TRUE),
    (24, 'Squash',                 TRUE),
    (25, 'Pádel',                  TRUE),
    -- Combate
    (26, 'Boxeo',                  TRUE),
    (27, 'Judo',                   TRUE),
    (28, 'Karate-Do',              TRUE),
    (29, 'Taekwondo',              TRUE),
    (30, 'Lucha',                  TRUE),
    (31, 'Esgrima',                TRUE),
    (32, 'Capoeira',               TRUE),
    -- Tiempo y marca / acuáticos
    (33, 'Deportes subacuáticos',  TRUE),
    (34, 'Ciclomontañismo',        TRUE),
    (35, 'BMX',                    TRUE),
    (36, 'Levantamiento de pesas', TRUE),
    -- Gimnasia / arte
    (37, 'Gimnasia',               TRUE),
    (38, 'Porras (cheerleading)',  TRUE),
    -- Precisión / mente
    (39, 'Arquería',               TRUE),
    (40, 'Bolos',                  TRUE),
    -- Urbanas
    (41, 'Escalada',               TRUE),
    (42, 'Skateboarding',          TRUE)
ON CONFLICT (nombre) DO UPDATE SET activo = TRUE;

-- ── Opcionales confirmadas (entran: se practican mucho en Bogotá) ───────────
INSERT INTO disciplina_deportiva (codigo, nombre, activo)
OVERRIDING SYSTEM VALUE VALUES
    (43, 'Jiu-Jitsu',                   TRUE),
    (44, 'Muay Thai / Kickboxing',      TRUE),
    (45, 'Calistenia / Street Workout', TRUE)
ON CONFLICT (nombre) DO UPDATE SET activo = TRUE;

-- ── Reset de la secuencia IDENTITY (cubre el MAX final) ─────────────────────
SELECT setval('public.disciplina_deportiva_codigo_seq',
              (SELECT MAX(codigo) FROM disciplina_deportiva));

COMMIT;

-- ============================================================================
-- ROLLBACK (best-effort; relabel/deactivate se restauran desde snapshot).
-- ============================================================================
-- BEGIN;
-- DELETE FROM disciplina_deportiva WHERE codigo BETWEEN 15 AND 45;
-- UPDATE disciplina_deportiva SET activo = TRUE     WHERE codigo = 5;   -- 'Artes marciales'
-- UPDATE disciplina_deportiva SET nombre = 'Futsala' WHERE codigo = 1;
-- SELECT setval('public.disciplina_deportiva_codigo_seq',
--               (SELECT MAX(codigo) FROM disciplina_deportiva));
-- COMMIT;
