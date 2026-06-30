-- ============================================================================
-- Banco de Iniciativas #62 — QA Lote 3 (catálogos: APPEND + DEACTIVATE)
-- Fecha: 2026-06-30 · Rama: feat/banco-qa-#62
--
-- REGLA: append de códigos nuevos + marcar viejos activo=False. NUNCA se
-- remapean ni borran las 24 inscripciones reales (siguen apuntando a los
-- códigos legacy inactivos, que el form resuelve para mostrar el histórico).
-- Ningún remap automático (decisión Alex). Snapshot de catálogos previo
-- obligatorio (es la vía de restore real para las filas REUSADAS).
--
-- NO LO CORRE CLAUDE solo: lo corre tras snapshot + revisión de Alex.
-- Idempotente. Atómico (BEGIN/COMMIT).
--
-- ── FIX vs. corridas previas (aprobado por Alex) ────────────────────────────
--  1) escenario/tipo_organizacion/rango_etario.codigo = GENERATED ALWAYS AS
--     IDENTITY → INSERT con código explícito requiere OVERRIDING SYSTEM VALUE.
--  2) Tienen UNIQUE(nombre). Dos nombres YA EXISTEN con código legacy:
--        - escenario 'Pista de atletismo' (codigo 7, activo)
--        - tipo_organizacion 'Colectivo con carta de conformación' (codigo 3)
--     ON CONFLICT (codigo) NO los atrapa. Estrategia: DESACTIVAR primero los
--     legacy, luego INSERT ... ON CONFLICT (nombre) DO UPDATE SET activo=TRUE
--     (REUSA la fila existente, recategorizándola). No se duplica el nombre.
--  3) Tras los inserts manuales la secuencia IDENTITY no avanzó → setval()
--     dentro de la misma transacción para que el próximo alta automática
--     (sin código) no choque.
--
--  NOTA 'Pista de atletismo': al reusarla pasa a categoria_pot='red_estructurante'.
--  Cambia la categoría para cualquier registro histórico que la referencie.
--  Correcto (ES red estructurante), queda anotado.
--
-- Decisión de modelado U-04: los 3 textos por bloque (Nombre/Dirección/
-- Actividad) van en tabla `inscripcion_banco_red_detalle` (1 fila por red).
-- ============================================================================

BEGIN;

-- ── M-01 · territorial — RESUELTO FUERA DE ESTE SCRIPT (Opción A) ───────────
-- Deportes confirmó: UPL y UPZ COEXISTEN (dos listas independientes), NO es
-- reemplazo. El enfoque original (meter UPZ en `upl` y desactivar 1-9) queda
-- DESCARTADO. `upl` se conserva intacto (9 activas). El 2º desplegable reusa
-- la tabla `upz` existente (georeferenciación, 12 oficiales + geometría) vía
-- una columna nueva `inscripcion_banco_iniciativa.upz_codigo → upz(codigo)`
-- (script aparte, pendiente de confirmar el contenido del catálogo con Deportes).
-- Aquí NO se toca territorial.

-- ── M-05 · rango_etario → 7 oficiales (deactivate-first + upsert nombre) ─────
UPDATE rango_etario SET activo = FALSE WHERE codigo BETWEEN 1 AND 5;
INSERT INTO rango_etario (codigo, nombre, edad_min, edad_max, activo, orden)
OVERRIDING SYSTEM VALUE VALUES
    (6,  'Primera infancia (0-5)',          0,  5,    TRUE, 1),
    (7,  'Infancia (6-11)',                 6,  11,   TRUE, 2),
    (8,  'Adolescencia (12-17)',            12, 17,   TRUE, 3),
    (9,  'Juventud (18-28)',                18, 28,   TRUE, 4),
    (10, 'Adultez (29-59)',                 29, 59,   TRUE, 5),
    (11, 'Vejez – Persona Mayor (60+)',     60, 120,  TRUE, 6),
    (12, 'Familias (intergeneracionales)',  NULL, NULL, TRUE, 7)
ON CONFLICT (nombre) DO UPDATE SET
    activo = TRUE, edad_min = EXCLUDED.edad_min,
    edad_max = EXCLUDED.edad_max, orden = EXCLUDED.orden;
SELECT setval('public.rango_etario_codigo_seq', (SELECT MAX(codigo) FROM rango_etario));

-- ── U-02 · tipo_organizacion → 4 (deactivate-first + upsert nombre) ──────────
UPDATE tipo_organizacion SET activo = FALSE WHERE codigo BETWEEN 1 AND 5;
INSERT INTO tipo_organizacion (codigo, nombre, activo, orden)
OVERRIDING SYSTEM VALUE VALUES
    (6, 'Club con reconocimiento deportivo vigente', TRUE, 1),
    (7, 'Escuela con aval deportivo vigente',        TRUE, 2),
    (8, 'Personería jurídica',                       TRUE, 3),
    (9, 'Colectivo con carta de conformación',       TRUE, 4)  -- reusa codigo 3
ON CONFLICT (nombre) DO UPDATE SET
    activo = TRUE, orden = EXCLUDED.orden;
SELECT setval('public.tipo_organizacion_codigo_seq', (SELECT MAX(codigo) FROM tipo_organizacion));

-- ── U-04 · escenario → espacios por red (deactivate-first + upsert nombre) ───
-- categoria_pot deja de ser un CHECK de 3 valores (duplicaba a `red`, que ya
-- tiene 4) y pasa a ser FK → red(codigo). Una 5ª "red" futura = INSERT en red,
-- sin cirugía de constraint. Verificado: todo valor actual ∈ red(codigo), sin
-- huérfanos, y `red` ya contiene 'otros_practica' (creada en lote 2).
UPDATE escenario SET activo = FALSE WHERE codigo BETWEEN 1 AND 17;
ALTER TABLE escenario DROP CONSTRAINT escenario_categoria_pot_check;
INSERT INTO escenario (codigo, nombre, categoria_pot, activo, orden)
OVERRIDING SYSTEM VALUE VALUES
    -- Red estructurante
    (18, 'Piscina cubierta',                 'red_estructurante', TRUE, 1),
    (19, 'Coliseo',                          'red_estructurante', TRUE, 2),
    (20, 'Pista de atletismo',               'red_estructurante', TRUE, 3),  -- reusa codigo 7
    (21, 'Patinódromo',                      'red_estructurante', TRUE, 4),
    (22, 'Pista BMX',                        'red_estructurante', TRUE, 5),
    (23, 'Cancha de fútbol 11',              'red_estructurante', TRUE, 6),
    (24, 'Cancha múltiple en asfalto',       'red_estructurante', TRUE, 7),
    (25, 'Cancha de microfútbol/baloncesto', 'red_estructurante', TRUE, 8),
    (26, 'Canchas de tenis',                 'red_estructurante', TRUE, 9),
    -- Red de proximidad
    (27, 'Cancha sintética comunitaria',     'red_proximidad', TRUE, 10),
    (28, 'Cancha múltiple asfalto/cemento',  'red_proximidad', TRUE, 11),
    (29, 'Cancha de microfútbol barrial',    'red_proximidad', TRUE, 12),
    (30, 'Cancha de baloncesto barrial',     'red_proximidad', TRUE, 13),
    (31, 'Gimnasio al aire libre',           'red_proximidad', TRUE, 14),
    (32, 'Calistenia',                       'red_proximidad', TRUE, 15),
    (33, 'NTD/Skatepark',                    'red_proximidad', TRUE, 16),
    (34, 'Parques infantiles',               'red_proximidad', TRUE, 17),
    (35, 'Juegos tradicionales',             'red_proximidad', TRUE, 18),
    -- Otros espacios dotacionales y ambientales
    (36, 'Salón comunal/CDC/Casa joven',     'otros_dotacionales', TRUE, 19),
    (37, 'Plazoletas/Plazas/Alamedas',       'otros_dotacionales', TRUE, 20),
    (38, 'Entornos ambientales (humedales)', 'otros_dotacionales', TRUE, 21),
    (39, 'Ciclo-infraestructura',            'otros_dotacionales', TRUE, 22),
    (40, 'Colegios públicos en convenio',    'otros_dotacionales', TRUE, 23),
    -- Otros espacios de práctica
    (41, 'Zonas verdes / "Potreros"',        'otros_practica', TRUE, 24),
    (42, 'Vía pública',                      'otros_practica', TRUE, 25),
    (43, 'Escenario deportivo privado',      'otros_practica', TRUE, 26),
    (44, 'Sede propia',                      'otros_practica', TRUE, 27),
    (45, 'Sin escenario fijo (Itinerante)',  'otros_practica', TRUE, 28)
ON CONFLICT (nombre) DO UPDATE SET
    activo = TRUE, categoria_pot = EXCLUDED.categoria_pot, orden = EXCLUDED.orden;
SELECT setval('public.escenario_codigo_seq', (SELECT MAX(codigo) FROM escenario));
-- categoria_pot ahora FK → red(codigo) (nullable: escenarios viejos en NULL).
ALTER TABLE escenario ADD CONSTRAINT escenario_categoria_pot_fk
    FOREIGN KEY (categoria_pot) REFERENCES red(codigo);

-- U-04 · 3 textos por bloque (Nombre/Dirección/Actividad) → tabla, 1 fila/red.
CREATE TABLE IF NOT EXISTS inscripcion_banco_red_detalle (
    id BIGSERIAL UNIQUE,
    inscripcion_id BIGINT      NOT NULL REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    red_codigo     VARCHAR(40) NOT NULL REFERENCES red(codigo),
    nombre    VARCHAR(50),
    direccion VARCHAR(50),
    actividad VARCHAR(50),
    PRIMARY KEY (inscripcion_id, red_codigo)
);

COMMIT;

-- ============================================================================
-- ROLLBACK (best-effort). Las 24 filas NO se tocan. Las filas REUSADAS
-- (escenario codigo 7 'Pista de atletismo' y tipo_organizacion codigo 3
-- 'Colectivo…') quedaron recategorizadas/reactivadas → se restauran desde el
-- SNAPSHOT de catálogos, no desde aquí.
-- NOTA: territorial (upl) NO se tocó en este lote (HOLD M-01).
-- ============================================================================
-- BEGIN;
-- DROP TABLE IF EXISTS inscripcion_banco_red_detalle;
-- ALTER TABLE escenario DROP CONSTRAINT escenario_categoria_pot_fk;
-- DELETE FROM escenario          WHERE codigo BETWEEN 18 AND 45;
-- DELETE FROM tipo_organizacion  WHERE codigo BETWEEN 6 AND 9;
-- DELETE FROM rango_etario       WHERE codigo BETWEEN 6 AND 12;
-- UPDATE escenario          SET activo = TRUE WHERE codigo BETWEEN 1 AND 17;  -- categoria_pot de cod 7 ← snapshot
-- UPDATE tipo_organizacion  SET activo = TRUE WHERE codigo BETWEEN 1 AND 5;
-- UPDATE rango_etario       SET activo = TRUE WHERE codigo BETWEEN 1 AND 5;
-- SELECT setval('public.escenario_codigo_seq',         (SELECT MAX(codigo) FROM escenario));
-- SELECT setval('public.tipo_organizacion_codigo_seq', (SELECT MAX(codigo) FROM tipo_organizacion));
-- SELECT setval('public.rango_etario_codigo_seq',      (SELECT MAX(codigo) FROM rango_etario));
-- ALTER TABLE escenario ADD CONSTRAINT escenario_categoria_pot_check
--     CHECK (categoria_pot IS NULL OR categoria_pot IN
--            ('red_estructurante','red_proximidad','otros_dotacionales'));
-- COMMIT;
