-- ============================================================================
-- Banco de Iniciativas #62 — QA Lote 3 (catálogos: APPEND + DEACTIVATE)
-- Fecha: 2026-06-30 · Rama: feat/banco-qa-#62
--
-- REGLA: append de códigos nuevos + marcar viejos activo=False. NUNCA se
-- remapean ni borran las 24 inscripciones reales (siguen apuntando a los
-- códigos legacy inactivos, que resuelven para mostrar histórico). Ningún
-- remap automático (decisión Alex). Snapshot previo obligatorio.
--
-- NO LO CORRE CLAUDE. Lo revisa y lo corre Alex. Tablas managed=False.
-- Idempotente (ON CONFLICT DO NOTHING + UPDATEs). Atómico (BEGIN/COMMIT).
--
-- Decisión de modelado U-04: los 3 textos por bloque (Nombre/Dirección/
-- Actividad) van en tabla `inscripcion_banco_red_detalle` (1 fila por red),
-- no en 12 columnas sueltas. CONFIRMAR en revisión.
-- ============================================================================

BEGIN;

-- ── M-01 · upl → 6 UPZ oficiales (append) + viejas inactivas ────────────────
INSERT INTO upl (codigo, nombre, activo, orden) VALUES
    (10, 'UPZ Kennedy', TRUE, 1), (11, 'UPZ Tintal', TRUE, 2),
    (12, 'UPZ Patio Bonito', TRUE, 3), (13, 'UPZ Britalia', TRUE, 4),
    (14, 'UPZ Edén', TRUE, 5), (15, 'UPZ Las Delicias', TRUE, 6)
ON CONFLICT (codigo) DO NOTHING;
UPDATE upl SET activo = FALSE WHERE codigo BETWEEN 1 AND 9;

-- ── M-05 · rango_etario → 7 oficiales (append) + viejos inactivos ───────────
INSERT INTO rango_etario (codigo, nombre, edad_min, edad_max, activo, orden) VALUES
    (6,  'Primera infancia (0-5)',          0,  5,    TRUE, 1),
    (7,  'Infancia (6-11)',                 6,  11,   TRUE, 2),
    (8,  'Adolescencia (12-17)',            12, 17,   TRUE, 3),
    (9,  'Juventud (18-28)',                18, 28,   TRUE, 4),
    (10, 'Adultez (29-59)',                 29, 59,   TRUE, 5),
    (11, 'Vejez – Persona Mayor (60+)',     60, 120,  TRUE, 6),
    (12, 'Familias (intergeneracionales)',  NULL, NULL, TRUE, 7)
ON CONFLICT (codigo) DO NOTHING;
UPDATE rango_etario SET activo = FALSE WHERE codigo BETWEEN 1 AND 5;

-- ── U-02 · tipo_organizacion → 4 (append) + viejos inactivos ────────────────
INSERT INTO tipo_organizacion (codigo, nombre, activo, orden) VALUES
    (6, 'Club con reconocimiento deportivo vigente', TRUE, 1),
    (7, 'Escuela con aval deportivo vigente',        TRUE, 2),
    (8, 'Personería jurídica',                       TRUE, 3),
    (9, 'Colectivo con carta de conformación',       TRUE, 4)
ON CONFLICT (codigo) DO NOTHING;
UPDATE tipo_organizacion SET activo = FALSE WHERE codigo BETWEEN 1 AND 5;

-- ── U-04 · escenario → espacios por red (append) + viejos inactivos ─────────
INSERT INTO escenario (codigo, nombre, categoria_pot, activo, orden) VALUES
    -- Red estructurante
    (18, 'Piscina cubierta',                 'red_estructurante', TRUE, 1),
    (19, 'Coliseo',                          'red_estructurante', TRUE, 2),
    (20, 'Pista de atletismo',               'red_estructurante', TRUE, 3),
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
ON CONFLICT (codigo) DO NOTHING;
UPDATE escenario SET activo = FALSE WHERE codigo BETWEEN 1 AND 17;

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
-- ROLLBACK (deshace lote 3; las 24 filas NO se tocan — referencian códigos
-- legacy 1..N que aquí se REACTIVAN; los códigos nuevos no tienen referencias
-- porque el form de lote 3 aún no está desplegado).
-- ============================================================================
-- BEGIN;
-- DROP TABLE IF EXISTS inscripcion_banco_red_detalle;
-- DELETE FROM escenario          WHERE codigo BETWEEN 18 AND 45;
-- DELETE FROM tipo_organizacion  WHERE codigo BETWEEN 6 AND 9;
-- DELETE FROM rango_etario       WHERE codigo BETWEEN 6 AND 12;
-- DELETE FROM upl                WHERE codigo BETWEEN 10 AND 15;
-- UPDATE escenario          SET activo = TRUE WHERE codigo BETWEEN 1 AND 17;
-- UPDATE tipo_organizacion  SET activo = TRUE WHERE codigo BETWEEN 1 AND 5;
-- UPDATE rango_etario       SET activo = TRUE WHERE codigo BETWEEN 1 AND 5;
-- UPDATE upl                SET activo = TRUE WHERE codigo BETWEEN 1 AND 9;
-- COMMIT;
