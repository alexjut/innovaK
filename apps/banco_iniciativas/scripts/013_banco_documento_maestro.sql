-- ============================================================================
-- Banco de Iniciativas — DDL del DOCUMENTO MAESTRO oficial (Deportes, 2026-07-29)
-- Fecha: 2026-07-29 · Frente A, PR-1 (ver docs/propuestas/plan_trabajo_2026-07-29.md)
--
-- QUÉ ES ESTO
--   El Documento Maestro (27 pág.) redefine el formulario del Banco en 9
--   secciones y la matriz en 100 puntos. Este script crea ÚNICAMENTE lo que
--   HOY NO EXISTE en `poblacion_kennedy`, verificado columna por columna
--   contra information_schema el 2026-07-29.
--
-- QUÉ *NO* HACE (a propósito)
--   · NO borra ni renombra nada. Las 24 inscripciones del piloto (evento 62)
--     siguen legibles con sus columnas actuales. Lo que el plan marca como
--     "se borra" del formulario se retira del FORM, no del schema: borrar
--     columnas con dato histórico es pérdida irreversible y va en otro PR,
--     con decisión explícita.
--   · NO toca el motor de puntaje (`services/matriz_oficial.py`, PR-2).
--   · NO define pesos ni topes en la BD. La rúbrica vive en el código y se
--     congela en `banco_rubrica.config` (patrón del script 008). Acá solo
--     hay estructura para CAPTURAR el dato.
--
-- CONVENCIONES QUE SÍ RESPETA
--   · PKs BIGSERIAL en todas las tablas hijas nuevas. Ninguna nace con la
--     deuda de MAX(id)+1.
--   · Sin prefijo `public.` en los nombres de tabla.
--   · Idempotente (IF NOT EXISTS / ON CONFLICT DO NOTHING) y atómico.
--   · Catálogos con el patrón "append + deactivate": nunca se edita una fila
--     que ya referencian inscripciones; se agrega la nueva y se apaga la
--     vieja con activo=FALSE. Así el histórico sigue resolviendo su FK.
--
-- ⚠️  NO LO CORRE CLAUDE. Lo revisa y lo aplica Alex, con backup < 24 h.
--     Rollback en 013_banco_documento_maestro_rollback.sql.
--
-- ORDEN DEL SCRIPT
--   A. Catálogos nuevos            (§4.1/§7.3, §6.1, §5.2/§7.8)
--   B. Realineación de catálogos   (§1.9, §3.2, §3.4, §4.2/§7.9.1, §6.2)
--   C. Columnas nuevas de cabecera (§2, §3.1, §4.1, §4.2, §6.2, §7.x, §8.1, §9)
--   D. Tablas hijas nuevas         (§5.2/§7.8, §6.1, §7.4.2, §8.2-§8.5, anexos)
-- ============================================================================

BEGIN;

-- ============================================================================
-- A. CATÁLOGOS NUEVOS
-- ============================================================================

-- A.1 · §4.1 y §7.3 — modalidad recreodeportiva.
-- Hoy §4.1 se captura como texto libre (`actividad_principal VARCHAR(150)`).
-- El documento la cierra a 5 opciones y la repite en §7.3 para la propuesta.
-- Catálogo propio: son modalidades, no disciplinas (`disciplina_deportiva`
-- sigue siendo el submenú de segundo nivel de ambas preguntas).
CREATE TABLE IF NOT EXISTS modalidad_recreodeportiva (
    codigo  SMALLINT PRIMARY KEY,
    nombre  TEXT     NOT NULL,
    activo  BOOLEAN  NOT NULL DEFAULT TRUE,
    orden   SMALLINT
);

INSERT INTO modalidad_recreodeportiva (codigo, nombre, orden) VALUES
    (1, 'Actividad física',      1),
    (2, 'Recreación',            2),
    (3, 'Recreación y deporte',  3),
    (4, 'Festival deportivo',    4),
    (5, 'Competencia deportiva', 5)
ON CONFLICT (codigo) DO NOTHING;


-- A.2 · §6.1 — instancias de concertación ciudadana (multiselección).
-- Hoy §6.1 es un select ÚNICO (`espacio_participacion VARCHAR(60)`) con otra
-- lista (DRAFE, mesas técnicas, CLJ, consejo de discapacidad). El documento
-- pide multiselección sobre 5 opciones distintas y puntúa +1 por opción
-- (tope 2). Catálogo nuevo + tabla puente en la sección D.
--
-- OJO: el nombre `instancia_participacion` YA ESTÁ TOMADO en la BD por una
-- tabla de caracterización (columnas caracterizacion_id/entidad/rol). De ahí
-- el nombre `instancia_concertacion`.
CREATE TABLE IF NOT EXISTS instancia_concertacion (
    codigo  SMALLINT PRIMARY KEY,
    nombre  TEXT     NOT NULL,
    activo  BOOLEAN  NOT NULL DEFAULT TRUE,
    orden   SMALLINT
);

INSERT INTO instancia_concertacion (codigo, nombre, orden) VALUES
    (1, 'Mesas del Plan de Desarrollo Local (PDL)', 1),
    (2, 'Presupuestos Participativos',              2),
    (3, 'DRAFE',                                    3),
    (4, 'Consejos Locales',                         4),
    (5, 'Veedurías Ciudadanas',                     5)
ON CONFLICT (codigo) DO NOTHING;


-- A.3 · §5.2 y §7.8 — enfoques con SUBMENÚS EN CASCADA.
--
-- POR QUÉ UN CATÁLOGO DE DOS NIVELES Y NO MÁS COLUMNAS:
--   El documento pide lo mismo dos veces con listas distintas: §5.2 (6
--   familias puntuables + "Ninguno", caracterización) y §7.8 (10 familias +
--   "Ninguno", propuesta). Cada familia abre su propio submenú. Modelarlo
--   con una tabla por dimensión —como hizo el Lote 4— produjo 8 catálogos y
--   8 puentes; agregar 16 familias más por el mismo camino son 30 tablas.
--
--   Acá la jerarquía es dato, no schema: familia → opciones. Agregar una
--   familia o una subopción pasa a ser un INSERT, no un DDL.
--
--   `seccion` discrimina las dos listas. NO es denormalización suelta: la
--   UNIQUE (codigo, seccion) permite que la tabla de selección referencie el
--   par completo, así que la BD impide que una selección de §7.8 apunte a
--   una familia de §5.2.
--
-- Los catálogos del Lote 4 (tipo_discapacidad, grupo_etnico_banco, …) NO se
-- tocan: sostienen las 24 inscripciones históricas y el form viejo.
CREATE TABLE IF NOT EXISTS banco_enfoque_familia (
    codigo   VARCHAR(40) PRIMARY KEY,
    seccion  VARCHAR(4)  NOT NULL,
    nombre   TEXT        NOT NULL,
    activo   BOOLEAN     NOT NULL DEFAULT TRUE,
    orden    SMALLINT,
    CONSTRAINT ck_banco_enfoque_familia_seccion CHECK (seccion IN ('5.2', '7.8')),
    -- Necesaria para la FK compuesta desde la tabla de selección.
    CONSTRAINT uq_banco_enfoque_familia_cod_sec UNIQUE (codigo, seccion)
);

CREATE TABLE IF NOT EXISTS banco_enfoque_opcion (
    codigo          VARCHAR(60) PRIMARY KEY,
    familia_codigo  VARCHAR(40) NOT NULL REFERENCES banco_enfoque_familia(codigo),
    nombre          TEXT        NOT NULL,
    activo          BOOLEAN     NOT NULL DEFAULT TRUE,
    orden           SMALLINT
);
CREATE INDEX IF NOT EXISTS idx_banco_enfoque_opcion_familia
    ON banco_enfoque_opcion (familia_codigo);

-- ── Seed §5.2 (6 familias puntuables + Ninguno) ──
INSERT INTO banco_enfoque_familia (codigo, seccion, nombre, orden) VALUES
    ('c52_mujer_genero',      '5.2', 'Mujer y Género',                        1),
    ('c52_discapacidad',      '5.2', 'Discapacidad',                          2),
    ('c52_etnico_narp',       '5.2', 'Étnico - Comunidades NARP',             3),
    ('c52_etnico_indigena',   '5.2', 'Étnico - Comunidades Indígenas',        4),
    ('c52_victima',           '5.2', 'Población Víctima del Conflicto Armado', 5),
    ('c52_habitabilidad',     '5.2', 'Habitabilidad en Calle y Riesgo Social', 6),
    ('c52_ninguno',           '5.2', 'Ninguno',                               99)
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO banco_enfoque_opcion (codigo, familia_codigo, nombre, orden) VALUES
    ('c52_mujer_genero__femenino',       'c52_mujer_genero',    'Femenino',      1),
    ('c52_mujer_genero__masculino',      'c52_mujer_genero',    'Masculino',     2),
    ('c52_mujer_genero__transgenero',    'c52_mujer_genero',    'Transgénero',   3),
    ('c52_mujer_genero__no_binario',     'c52_mujer_genero',    'No binario',    4),

    ('c52_discapacidad__auditiva',       'c52_discapacidad',    'Auditiva',      1),
    ('c52_discapacidad__fisica',         'c52_discapacidad',    'Física',        2),
    ('c52_discapacidad__intelectual',    'c52_discapacidad',    'Intelectual',   3),
    ('c52_discapacidad__visual',         'c52_discapacidad',    'Visual',        4),
    ('c52_discapacidad__sordoceguera',   'c52_discapacidad',    'Sordo-Ceguera', 5),
    ('c52_discapacidad__psicosocial',    'c52_discapacidad',    'Psicosocial',   6),
    ('c52_discapacidad__multiple',       'c52_discapacidad',    'Múltiple',      7),

    ('c52_etnico_narp__negros',          'c52_etnico_narp',     'Negros/as',        1),
    ('c52_etnico_narp__afro',            'c52_etnico_narp',     'Afrodescendientes', 2),
    ('c52_etnico_narp__palenquero',      'c52_etnico_narp',     'Palenquero/a',     3),
    ('c52_etnico_narp__raizal',          'c52_etnico_narp',     'Raizal',           4),

    ('c52_etnico_indigena__muisca',      'c52_etnico_indigena', 'Muisca',        1),
    ('c52_etnico_indigena__inga',        'c52_etnico_indigena', 'Inga',          2),
    ('c52_etnico_indigena__kubeo',       'c52_etnico_indigena', 'Kubeo',         3),
    ('c52_etnico_indigena__ambika',      'c52_etnico_indigena', 'Ambiká Pijao',  4),
    ('c52_etnico_indigena__nasa',        'c52_etnico_indigena', 'Nasa',          5),
    ('c52_etnico_indigena__otro_cabildo', 'c52_etnico_indigena', 'Otro Cabildo Registrado', 6),

    ('c52_victima__ruv',                 'c52_victima',         'Población con registro RUV',      1),
    ('c52_victima__desplazamiento',      'c52_victima',         'Desplazamiento forzado',          2),
    ('c52_victima__reparacion_colectiva', 'c52_victima',        'Sujeto de reparación colectiva',  3),

    ('c52_habitabilidad__habitante',     'c52_habitabilidad',   'Habitante de calle',                    1),
    ('c52_habitabilidad__riesgo',        'c52_habitabilidad',   'Personas en riesgo de habitar la calle', 2),
    ('c52_habitabilidad__jovenes',       'c52_habitabilidad',   'Jóvenes en vulnerabilidad extrema',      3)
ON CONFLICT (codigo) DO NOTHING;

-- ── Seed §7.8 (10 familias + Ninguno) ──
INSERT INTO banco_enfoque_familia (codigo, seccion, nombre, orden) VALUES
    ('p78_mujer',            '7.8', 'Mujer',                                  1),
    ('p78_genero',           '7.8', 'Género',                                 2),
    ('p78_discapacidad',     '7.8', 'Discapacidad',                           3),
    ('p78_etnico_narp',      '7.8', 'Étnico - Comunidades NARP',              4),
    ('p78_etnico_indigena',  '7.8', 'Étnico - Comunidades Indígenas',         5),
    ('p78_etnico_rom',       '7.8', 'Étnico - Comunidad Rom',                 6),
    ('p78_victima',          '7.8', 'Población Víctima del Conflicto Armado', 7),
    ('p78_habitabilidad',    '7.8', 'Habitabilidad en Calle y Riesgo Social', 8),
    ('p78_migrante',         '7.8', 'Población Migrante y Transfronteriza',   9),
    ('p78_campesina',        '7.8', 'Población Campesina o Rural',           10),
    ('p78_ninguno',          '7.8', 'Ninguno',                               99)
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO banco_enfoque_opcion (codigo, familia_codigo, nombre, orden) VALUES
    ('p78_mujer__liderazgo',          'p78_mujer',       'Liderazgo comunitario',     1),
    ('p78_mujer__emprendimiento',     'p78_mujer',       'Emprendimiento recreativo', 2),
    ('p78_mujer__madres',             'p78_mujer',       'Madres comunitarias',       3),

    ('p78_genero__orientacion',       'p78_genero',      'Orientación sexual',              1),
    ('p78_genero__lgtbiq',            'p78_genero',      'Sectores LGTBIQ+ territoriales',  2),
    ('p78_genero__identidades',       'p78_genero',      'Identidades diversas',            3),

    ('p78_discapacidad__auditiva',     'p78_discapacidad', 'Auditiva',      1),
    ('p78_discapacidad__fisica',       'p78_discapacidad', 'Física',        2),
    ('p78_discapacidad__intelectual',  'p78_discapacidad', 'Intelectual',   3),
    ('p78_discapacidad__visual',       'p78_discapacidad', 'Visual',        4),
    ('p78_discapacidad__sordoceguera', 'p78_discapacidad', 'Sordo-Ceguera', 5),
    ('p78_discapacidad__psicosocial',  'p78_discapacidad', 'Psicosocial',   6),
    ('p78_discapacidad__multiple',     'p78_discapacidad', 'Múltiple',      7),

    ('p78_etnico_narp__negros',        'p78_etnico_narp', 'Negros/as',         1),
    ('p78_etnico_narp__afro',          'p78_etnico_narp', 'Afrodescendientes', 2),
    ('p78_etnico_narp__palenquero',    'p78_etnico_narp', 'Palenquero/a',      3),
    ('p78_etnico_narp__raizal',        'p78_etnico_narp', 'Raizal',            4),

    ('p78_etnico_indigena__muisca',    'p78_etnico_indigena', 'Muisca',       1),
    ('p78_etnico_indigena__inga',      'p78_etnico_indigena', 'Inga',         2),
    ('p78_etnico_indigena__kubeo',     'p78_etnico_indigena', 'Kubeo',        3),
    ('p78_etnico_indigena__ambika',    'p78_etnico_indigena', 'Ambiká Pijao', 4),
    ('p78_etnico_indigena__nasa',      'p78_etnico_indigena', 'Nasa',         5),
    ('p78_etnico_indigena__otro_cabildo', 'p78_etnico_indigena', 'Otro Cabildo', 6),

    ('p78_etnico_rom__kumpania',       'p78_etnico_rom',  'Kumpania Rom / Gitana', 1),

    ('p78_victima__ruv',               'p78_victima',     'Registro RUV',            1),
    ('p78_victima__desplazamiento',    'p78_victima',     'Desplazamiento forzado',  2),

    ('p78_habitabilidad__habitante',   'p78_habitabilidad', 'Habitante de calle',                1),
    ('p78_habitabilidad__jovenes',     'p78_habitabilidad', 'Jóvenes en vulnerabilidad extrema', 2),

    ('p78_migrante__ppt',              'p78_migrante',    'Migrante regularizado / PPT', 1),
    ('p78_migrante__refugiado',        'p78_migrante',    'Refugiado',                   2),

    ('p78_campesina__habitante_rural', 'p78_campesina',   'Habitante rural Kennedy', 1),
    ('p78_campesina__productor',       'p78_campesina',   'Campesino productor',     2)
ON CONFLICT (codigo) DO NOTHING;


-- ============================================================================
-- B. REALINEACIÓN DE CATÁLOGOS EXISTENTES (append + deactivate)
--
-- Los rangos del documento NO coinciden con los que hay en BD. No se pueden
-- reetiquetar las filas viejas: las referencian las 24 inscripciones y
-- cambiarles el texto reescribe el pasado. Se agregan las nuevas y se apagan
-- las viejas (activo=FALSE); la FK del histórico sigue resolviendo.
-- ============================================================================

-- B.1 · §1.9 — nivel educativo del representante.
-- Falta "Saberes Empíricos / Líder Comunitario". `nivel_educativo` no tiene
-- columna `activo`; solo se agrega la fila.
INSERT INTO nivel_educativo (codigo, nombre, orden) VALUES
    (10, 'Saberes Empíricos / Líder Comunitario', 10)
ON CONFLICT (codigo) DO NOTHING;

-- B.2 · §3.2 — años de trayectoria COMUNITARIA DEL COLECTIVO.
-- La columna `anios_experiencia_codigo` existía como "experiencia del
-- representante"; el documento la redefine como trayectoria del colectivo,
-- con 5 bandas distintas (>8 / 6-8 / 4-6 / 2-4 / 1-2).
-- OVERRIDING SYSTEM VALUE: `codigo` es GENERATED ALWAYS AS IDENTITY en este
-- catálogo (verificado en information_schema el 2026-07-29). Los códigos NO
-- pueden quedar al azar: la rúbrica del motor mapea código → puntaje, y si el
-- número lo asigna la secuencia, el mismo formulario daría puntajes distintos
-- en desarrollo y en producción. Al final de la sección B se adelanta la
-- secuencia para que los INSERT automáticos futuros no colisionen.
INSERT INTO rango_experiencia (codigo, nombre, activo, orden)
OVERRIDING SYSTEM VALUE VALUES
    (6,  'Mínimo 1 año a 2 años',   TRUE, 1),
    (7,  'Más de 2 años a 4 años',  TRUE, 2),
    (8,  'Más de 4 años a 6 años',  TRUE, 3),
    (9,  'Más de 6 años a 8 años',  TRUE, 4),
    (10, 'Más de 8 años',           TRUE, 5)
ON CONFLICT (codigo) DO NOTHING;
UPDATE rango_experiencia SET activo = FALSE WHERE codigo BETWEEN 1 AND 5;

-- B.3 · §3.4 — «Cantidad actual de personas que beneficia o atiende».
-- Bandas nuevas: >80 / 51-80 / 21-50 / hasta 20. Las viejas (1-10, 11-20,
-- 21-50, >50) no son mapeables 1:1 → append + deactivate.
INSERT INTO rango_poblacion_atendida (codigo, nombre, activo, orden)
OVERRIDING SYSTEM VALUE VALUES
    (5, 'Hasta 20 personas',       TRUE, 1),
    (6, 'De 21 a 50 personas',     TRUE, 2),
    (7, 'De 51 a 80 personas',     TRUE, 3),
    (8, 'Más de 80 personas',      TRUE, 4)
ON CONFLICT (codigo) DO NOTHING;
UPDATE rango_poblacion_atendida SET activo = FALSE WHERE codigo BETWEEN 1 AND 4;

-- B.4 · §6.2 — escala inversa de democratización del fomento.
-- El documento la vuelve selección ÚNICA de 5 niveles. `tipo_beneficio_alk`
-- ya tiene 4 de los 5 (logístico, formación, eventos, infraestructura); le
-- faltan los dos extremos de la escala.
INSERT INTO tipo_beneficio_alk (codigo, nombre, activo, orden)
OVERRIDING SYSTEM VALUE VALUES
    (7, 'Sin apoyos previos recibidos de la ALK',      TRUE, 0),
    (8, 'Contratos o convenios económicos directos previos', TRUE, 9)
ON CONFLICT (codigo) DO NOTHING;

-- B.5 · §4.2 y §7.9.1 — botones dinámicos que faltan en `escenario`.
-- Los 4 niveles ya existen como `red` (red_estructurante / red_proximidad /
-- otros_dotacionales / otros_practica) y los botones como `escenario` con
-- `categoria_pot`. Solo faltan dos etiquetas del documento.
-- Sin ON CONFLICT: se guardan por nombre para no pisar códigos si alguien
-- ya los sembró con otro número.
INSERT INTO escenario (codigo, nombre, categoria_pot, activo, orden)
OVERRIDING SYSTEM VALUE
SELECT 46, 'Colegios privados', 'otros_dotacionales', TRUE, 46
WHERE NOT EXISTS (
    SELECT 1 FROM escenario WHERE nombre = 'Colegios privados' OR codigo = 46
);

INSERT INTO escenario (codigo, nombre, categoria_pot, activo, orden)
OVERRIDING SYSTEM VALUE
SELECT 47, 'Canchas sintéticas con cerramiento', 'red_estructurante', TRUE, 47
WHERE NOT EXISTS (
    SELECT 1 FROM escenario
     WHERE nombre = 'Canchas sintéticas con cerramiento' OR codigo = 47
);


-- B.6 · Adelantar las secuencias de identidad de los catálogos donde acabamos
-- de insertar códigos explícitos con OVERRIDING SYSTEM VALUE.
--
-- POR QUÉ: `codigo` es GENERATED ALWAYS AS IDENTITY en estos catálogos. Al
-- escribir el código a mano la secuencia NO avanza, así que sigue apuntando a
-- un número ya ocupado. El próximo INSERT que deje elegir a Postgres —por
-- ejemplo desde el admin de Django— reventaría con una violación de llave
-- primaria. Se empuja la secuencia por encima del máximo real.
--
-- `pg_get_serial_sequence` también resuelve la secuencia de las columnas de
-- identidad, no solo de los serial.
SELECT setval(pg_get_serial_sequence('rango_experiencia', 'codigo'),
              (SELECT max(codigo) FROM rango_experiencia));
SELECT setval(pg_get_serial_sequence('rango_poblacion_atendida', 'codigo'),
              (SELECT max(codigo) FROM rango_poblacion_atendida));
SELECT setval(pg_get_serial_sequence('tipo_beneficio_alk', 'codigo'),
              (SELECT max(codigo) FROM tipo_beneficio_alk));
SELECT setval(pg_get_serial_sequence('escenario', 'codigo'),
              (SELECT max(codigo) FROM escenario));


-- ============================================================================
-- C. COLUMNAS NUEVAS EN LA CABECERA `inscripcion_banco_iniciativa`
--
-- Todas NULLABLE. Las 24 inscripciones del piloto se llenaron con el
-- formulario anterior y no tienen estos datos; un NOT NULL con DEFAULT les
-- inventaría respuestas. La obligatoriedad se valida en el form, que es
-- donde el documento la exige.
-- ============================================================================

ALTER TABLE inscripcion_banco_iniciativa
    -- §2 · compuerta condicional de sede física (hoy se infiere de que
    -- barrio/dirección vengan vacíos, que no es lo mismo que declarar "no").
    ADD COLUMN IF NOT EXISTS tiene_sede_fisica BOOLEAN,

    -- §3.1 · tamaño del staff como NÚMERO EXACTO.
    -- Hoy solo existe `tamano_organizacion VARCHAR(20)` con rangos
    -- (1_3/4_10/10_20/mayor_20). Los brackets del documento (>41, 31-40,
    -- 21-30, mín 20) no son derivables de esos rangos: se necesita el entero.
    -- La columna de rangos se conserva para el histórico.
    ADD COLUMN IF NOT EXISTS tamano_staff_num INTEGER,

    -- §4.1 · actividad principal como select + submenú de disciplina.
    -- `actividad_principal VARCHAR(150)` (texto libre) queda como histórico.
    ADD COLUMN IF NOT EXISTS modalidad_actividad_codigo   SMALLINT,
    ADD COLUMN IF NOT EXISTS disciplina_actividad_codigo  SMALLINT,
    ADD COLUMN IF NOT EXISTS disciplina_actividad_otro    VARCHAR(150),

    -- §4.2 · clasificación de entornos: NIVEL (opción única, es lo que
    -- puntúa) + "Otro" + bloque de localización obligatorio.
    -- Los botones de selección múltiple de cada nivel NO necesitan tabla
    -- nueva: reusan `inscripcion_banco_escenario_actual` (escenarios donde
    -- la organización opera hoy), que ya existe y ya apunta a `escenario`.
    ADD COLUMN IF NOT EXISTS arraigo_red_codigo      VARCHAR(40),
    ADD COLUMN IF NOT EXISTS arraigo_escenario_otro  VARCHAR(150),
    ADD COLUMN IF NOT EXISTS arraigo_espacio_nombre  VARCHAR(150),
    ADD COLUMN IF NOT EXISTS arraigo_direccion       VARCHAR(200),
    -- La dirección no es texto libre: se captura contra Catastro con pin en
    -- el mapa y SE GUARDA con su coordenada. Misma regla que la sede
    -- (`direccion_lon`/`direccion_lat`, script 012).
    ADD COLUMN IF NOT EXISTS arraigo_lon             DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS arraigo_lat             DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS arraigo_estrato         SMALLINT,
    ADD COLUMN IF NOT EXISTS arraigo_actividad       TEXT,

    -- §6.2 · democratización: selección única sobre `tipo_beneficio_alk`.
    -- Reemplaza funcionalmente al par (beneficiada_alk BOOL + M2M
    -- beneficios_alk), que se conserva para el histórico.
    ADD COLUMN IF NOT EXISTS beneficio_alk_codigo    SMALLINT,

    -- §7.1 / §7.2 / §7.4.1 · narrativa de la iniciativa.
    -- Mínimos de longitud (200 caracteres) se validan en el form, no en la
    -- BD: son regla de captura, no invariante del dato.
    ADD COLUMN IF NOT EXISTS problematica            TEXT,
    ADD COLUMN IF NOT EXISTS justificacion           TEXT,
    ADD COLUMN IF NOT EXISTS objetivo_general        TEXT,

    -- §7.3 · modalidad de la PROPUESTA (la disciplina y el "Otros" ya viven
    -- en `disciplina_principal_codigo` / `otros_deportes`).
    ADD COLUMN IF NOT EXISTS modalidad_propuesta_codigo SMALLINT,

    -- §7.5 · los tres rangos de cobertura. Códigos cortos estables, mismo
    -- patrón que `personas_beneficiar`; las etiquetas viven en el form y los
    -- pesos en la rúbrica. NO se reusa `personas_beneficiar`: sus bandas
    -- (min_20/21_30/31_40/mas_41) son otras.
    ADD COLUMN IF NOT EXISTS cobertura_staff        VARCHAR(20),
    ADD COLUMN IF NOT EXISTS cobertura_comunidad    VARCHAR(20),
    ADD COLUMN IF NOT EXISTS cobertura_indirectos   VARCHAR(20),

    -- §7.7 · impacto en la diversidad de género DE LA PROPUESTA.
    -- Distinta de §3.3 `composicion_organizacion`, que describe a la
    -- organización. Son dos preguntas y dos puntajes.
    ADD COLUMN IF NOT EXISTS diversidad_genero_propuesta VARCHAR(30),

    -- §7.9.1 · nivel del espacio donde se EJECUTA (opción única, puntúa 9).
    -- Los botones múltiples reusan `inscripcion_banco_escenario`
    -- (escenarios requeridos por la propuesta), que ya existe.
    ADD COLUMN IF NOT EXISTS ejecucion_red_codigo     VARCHAR(40),
    ADD COLUMN IF NOT EXISTS ejecucion_escenario_otro VARCHAR(150),

    -- §7.9.2 · estrato del espacio de EJECUCIÓN.
    -- Hoy solo se guarda el estrato de la SEDE (`estrato` declarado y
    -- `estrato_ideca_org` certificado). El documento puntúa 9 puntos por el
    -- estrato del espacio donde se ejecuta, que puede ser otro barrio.
    --   · ejecucion_estrato        → lo que declara el proponente (1-4).
    --   · ejecucion_estrato_ideca  → lo que certifica la API de IDECA contra
    --                                la placa domiciliaria. ES EL QUE PUNTÚA.
    --                                NULL = no determinable; no se infiere.
    --   · ejecucion_fuera_kennedy  → se ubicó y NO está en Kennedy. Separa
    --                                el NULL "no sabemos" del NULL "no aplica"
    --                                (misma lógica que `fuera_kennedy`, 011).
    ADD COLUMN IF NOT EXISTS ejecucion_estrato        SMALLINT,
    ADD COLUMN IF NOT EXISTS ejecucion_estrato_ideca  SMALLINT,
    ADD COLUMN IF NOT EXISTS ejecucion_lon            DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS ejecucion_lat            DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS ejecucion_fuera_kennedy  BOOLEAN,
    ADD COLUMN IF NOT EXISTS ejecucion_geo_metodo     VARCHAR(20),

    -- §7.10 · sostenibilidad ambiental (binario + sustento).
    ADD COLUMN IF NOT EXISTS sostenibilidad_ambiental BOOLEAN,
    ADD COLUMN IF NOT EXISTS sostenibilidad_sustento  TEXT,

    -- §8.1 · metodología (0 puntos, requisito formal del IDRD).
    ADD COLUMN IF NOT EXISTS metodologia              TEXT,

    -- §9 · juramento de buena fe (Art. 83 CN) y sello de radicación.
    -- Los 3 compromisos de ley y el par cédula/fecha de firma YA EXISTEN
    -- (compromiso_redes, compromiso_carta_1ano, compromiso_actualizacion,
    -- firma_cedula, firma_fecha). Lo único que falta es la declaración
    -- juramentada, que es un checkbox distinto y jurídicamente separado.
    ADD COLUMN IF NOT EXISTS declaracion_buena_fe     BOOLEAN,
    ADD COLUMN IF NOT EXISTS radicado_at              TIMESTAMPTZ;

-- Los campos de espacio de ejecución nacieron con 50 caracteres. Un nombre
-- real ("Parque Metropolitano Cayetano Cañizares — cancha 3") no cabe.
-- Ampliar VARCHAR no reescribe la tabla en PG ≥ 9.2 y no pierde dato.
ALTER TABLE inscripcion_banco_iniciativa
    ALTER COLUMN nombre_espacio_ejecucion    TYPE VARCHAR(150),
    ALTER COLUMN direccion_espacio_ejecucion TYPE VARCHAR(200);

-- ── FKs de las columnas nuevas (db_column explícito en los modelos) ──
ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS fk_insc_banco_modalidad_actividad,
    ADD  CONSTRAINT fk_insc_banco_modalidad_actividad
         FOREIGN KEY (modalidad_actividad_codigo) REFERENCES modalidad_recreodeportiva(codigo);

ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS fk_insc_banco_modalidad_propuesta,
    ADD  CONSTRAINT fk_insc_banco_modalidad_propuesta
         FOREIGN KEY (modalidad_propuesta_codigo) REFERENCES modalidad_recreodeportiva(codigo);

ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS fk_insc_banco_disciplina_actividad,
    ADD  CONSTRAINT fk_insc_banco_disciplina_actividad
         FOREIGN KEY (disciplina_actividad_codigo) REFERENCES disciplina_deportiva(codigo);

ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS fk_insc_banco_arraigo_red,
    ADD  CONSTRAINT fk_insc_banco_arraigo_red
         FOREIGN KEY (arraigo_red_codigo) REFERENCES red(codigo);

ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS fk_insc_banco_ejecucion_red,
    ADD  CONSTRAINT fk_insc_banco_ejecucion_red
         FOREIGN KEY (ejecucion_red_codigo) REFERENCES red(codigo);

ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS fk_insc_banco_beneficio_alk,
    ADD  CONSTRAINT fk_insc_banco_beneficio_alk
         FOREIGN KEY (beneficio_alk_codigo) REFERENCES tipo_beneficio_alk(codigo);

-- ── CHECKs de las columnas nuevas ──
-- El documento elimina explícitamente el estrato 5 de las cajas de selección.
ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS ck_insc_banco_arraigo_estrato,
    ADD  CONSTRAINT ck_insc_banco_arraigo_estrato
         CHECK (arraigo_estrato IS NULL OR arraigo_estrato BETWEEN 1 AND 4);

ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS ck_insc_banco_ejecucion_estrato,
    ADD  CONSTRAINT ck_insc_banco_ejecucion_estrato
         CHECK (ejecucion_estrato IS NULL OR ejecucion_estrato BETWEEN 1 AND 4);

ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS ck_insc_banco_ejecucion_estrato_ideca,
    ADD  CONSTRAINT ck_insc_banco_ejecucion_estrato_ideca
         CHECK (ejecucion_estrato_ideca IS NULL OR ejecucion_estrato_ideca BETWEEN 1 AND 4);

-- Staff en personas. Sin tope superior: si alguien declara 5.000 el dato es
-- discutible, pero no es la BD la que debe negarlo.
ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS ck_insc_banco_tamano_staff_num,
    ADD  CONSTRAINT ck_insc_banco_tamano_staff_num
         CHECK (tamano_staff_num IS NULL OR tamano_staff_num >= 0);

-- Mismo bbox de Bogotá del script 012: ataja el (lat, lon) invertido, que
-- dibuja la iniciativa en el océano Índico.
ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS ck_insc_banco_arraigo_lonlat,
    ADD  CONSTRAINT ck_insc_banco_arraigo_lonlat CHECK (
        (arraigo_lon IS NULL AND arraigo_lat IS NULL)
        OR (arraigo_lon BETWEEN -74.6 AND -73.9 AND arraigo_lat BETWEEN 3.7 AND 4.9)
    );

ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS ck_insc_banco_ejecucion_lonlat,
    ADD  CONSTRAINT ck_insc_banco_ejecucion_lonlat CHECK (
        (ejecucion_lon IS NULL AND ejecucion_lat IS NULL)
        OR (ejecucion_lon BETWEEN -74.6 AND -73.9 AND ejecucion_lat BETWEEN 3.7 AND 4.9)
    );

-- Códigos cerrados de §7.5. Van en la BD porque son la llave con la que la
-- rúbrica busca el peso: un código mal escrito no puntúa y falla en silencio.
ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS ck_insc_banco_cobertura_staff,
    ADD  CONSTRAINT ck_insc_banco_cobertura_staff
         CHECK (cobertura_staff IS NULL
                OR cobertura_staff IN ('ge_50', '11_49', '4_10', 'min_3'));

ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS ck_insc_banco_cobertura_comunidad,
    ADD  CONSTRAINT ck_insc_banco_cobertura_comunidad
         CHECK (cobertura_comunidad IS NULL
                OR cobertura_comunidad IN ('gt_80', '51_80', '41_60', '21_40', 'min_20'));

ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS ck_insc_banco_cobertura_indirectos,
    ADD  CONSTRAINT ck_insc_banco_cobertura_indirectos
         CHECK (cobertura_indirectos IS NULL
                OR cobertura_indirectos IN ('gt_200', '101_200', '51_100', 'hasta_50'));

-- §7.7 · los 6 niveles de la escala de equidad estructural.
ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS ck_insc_banco_diversidad_genero,
    ADD  CONSTRAINT ck_insc_banco_diversidad_genero
         CHECK (diversidad_genero_propuesta IS NULL
                OR diversidad_genero_propuesta IN (
                    'solo_mujeres', 'mayor_mujeres', 'lgtbiq',
                    'mixta_diversidades', 'mayor_hombres', 'solo_hombres'));

-- §7.10 · si declara SÍ, el sustento es obligatorio. Esto sí es invariante
-- del dato: un "sí" sin sustento vale 6 puntos que nadie puede auditar.
ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS ck_insc_banco_sostenibilidad,
    ADD  CONSTRAINT ck_insc_banco_sostenibilidad CHECK (
        sostenibilidad_ambiental IS NOT TRUE
        OR (sostenibilidad_sustento IS NOT NULL AND length(btrim(sostenibilidad_sustento)) > 0)
    );

-- Índice para el mapa: "las iniciativas cuyo espacio de ejecución tiene punto".
CREATE INDEX IF NOT EXISTS idx_insc_banco_ejecucion_ubicada
    ON inscripcion_banco_iniciativa (ejecucion_lat, ejecucion_lon)
    WHERE ejecucion_lat IS NOT NULL;

COMMENT ON COLUMN inscripcion_banco_iniciativa.tamano_staff_num IS
    '§3.1 · Número exacto de personas activas del staff. Los brackets del '
    'Documento Maestro (>41 / 31-40 / 21-30 / mín 20) se liquidan sobre este '
    'entero, no sobre el rango legacy `tamano_organizacion`.';
COMMENT ON COLUMN inscripcion_banco_iniciativa.ejecucion_estrato_ideca IS
    '§7.9.2 · Estrato del espacio de EJECUCIÓN certificado por la API de IDECA. '
    'Es el que puntúa (9/6/3/1). NULL = no determinable: no se infiere del '
    'estrato declarado ni del de la sede.';
COMMENT ON COLUMN inscripcion_banco_iniciativa.arraigo_red_codigo IS
    '§4.2 · Nivel de entorno de práctica (opción única). Reusa el catálogo '
    '`red` (4 niveles POT). OJO: el peso de cada nivel está en disputa entre '
    'el cuerpo del documento (pág. 11) y la matriz de síntesis (pág. 22) — '
    'ver §A.5 de docs/propuestas/plan_trabajo_2026-07-29.md. La BD guarda el '
    'nivel; el peso lo decide la rúbrica.';


-- ============================================================================
-- D. TABLAS HIJAS NUEVAS
--    Todas con BIGSERIAL y ON DELETE CASCADE desde la inscripción.
-- ============================================================================

-- D.1 · §6.1 — instancias de concertación (multiselección, +1 c/u tope 2).
CREATE TABLE IF NOT EXISTS inscripcion_banco_instancia (
    id             BIGSERIAL PRIMARY KEY,
    inscripcion_id BIGINT   NOT NULL
                   REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    instancia_codigo SMALLINT NOT NULL REFERENCES instancia_concertacion(codigo),
    CONSTRAINT uq_insc_banco_instancia UNIQUE (inscripcion_id, instancia_codigo)
);
CREATE INDEX IF NOT EXISTS idx_insc_banco_instancia_insc
    ON inscripcion_banco_instancia (inscripcion_id);


-- D.2 · §5.2 y §7.8 — familias de enfoque seleccionadas.
--
-- ⚠️  ACÁ VIVE EL ORDEN DE ACTIVACIÓN DE §7.8.
--
--   El documento puntúa §7.8 de forma DECRECIENTE según el orden en que el
--   ciudadano marcó los chips: 1º = 4.0 pts, 2º = 3.0, 3º = 2.0, 4º = 1.0,
--   5º en adelante = 0.0. El puntaje no depende de QUÉ marcó sino de CUÁNDO
--   lo marcó, así que el orden es dato calificable: si se pierde, la
--   iniciativa no se puede recalcular ni defender ante una impugnación.
--
--   Un M2M normal no sirve: `insc.enfoques.set([...])` inserta en el orden
--   que le da la gana el motor y `SELECT` sin ORDER BY devuelve lo que
--   devuelva el plan de ejecución. Por eso la secuencia se materializa como
--   COLUMNA (`orden_activacion`) en la tabla puente, con UNIQUE por
--   inscripción y sección. Es el mismo motivo por el que existe
--   `InscripcionBancoRedDetalle`: cuando el puente lleva dato, deja de ser
--   un M2M y pasa a ser una tabla con derecho propio.
--
--   El UNIQUE también impide el empate silencioso (dos familias reclamando
--   ser "la primera"), que en una convocatoria de plata pública es la
--   diferencia entre entrar y no entrar al top 93.
--
--   Contigüidad (1,2,3… sin huecos) NO se puede expresar en un CHECK por
--   fila: la valida el servicio al guardar.
--
--   `seccion` viaja en la fila y la FK COMPUESTA (familia_codigo, seccion)
--   garantiza que coincida con la de la familia. No es denormalización
--   suelta: la BD no deja que diverja.
CREATE TABLE IF NOT EXISTS inscripcion_banco_enfoque_familia (
    id              BIGSERIAL PRIMARY KEY,
    inscripcion_id  BIGINT      NOT NULL
                    REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    familia_codigo  VARCHAR(40) NOT NULL,
    seccion         VARCHAR(4)  NOT NULL,
    -- 1 = primera etiqueta que activó el usuario.
    orden_activacion SMALLINT   NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_insc_banco_enfoque_familia
        FOREIGN KEY (familia_codigo, seccion)
        REFERENCES banco_enfoque_familia(codigo, seccion),
    CONSTRAINT ck_insc_banco_enfoque_orden CHECK (orden_activacion >= 1),
    -- Una familia se marca una sola vez.
    CONSTRAINT uq_insc_banco_enfoque_familia
        UNIQUE (inscripcion_id, familia_codigo),
    -- Y una posición la ocupa una sola familia (por sección).
    CONSTRAINT uq_insc_banco_enfoque_orden
        UNIQUE (inscripcion_id, seccion, orden_activacion)
);
CREATE INDEX IF NOT EXISTS idx_insc_banco_enfoque_familia_insc
    ON inscripcion_banco_enfoque_familia (inscripcion_id, seccion, orden_activacion);

-- Subopciones marcadas dentro de cada familia (los submenús en cascada).
-- No puntúan por sí solas: son caracterización. Cuelgan de la SELECCIÓN, no
-- de la inscripción, para que desmarcar la familia se lleve sus opciones.
CREATE TABLE IF NOT EXISTS inscripcion_banco_enfoque_opcion (
    id            BIGSERIAL PRIMARY KEY,
    seleccion_id  BIGINT      NOT NULL
                  REFERENCES inscripcion_banco_enfoque_familia(id) ON DELETE CASCADE,
    opcion_codigo VARCHAR(60) NOT NULL REFERENCES banco_enfoque_opcion(codigo),
    CONSTRAINT uq_insc_banco_enfoque_opcion UNIQUE (seleccion_id, opcion_codigo)
);
CREATE INDEX IF NOT EXISTS idx_insc_banco_enfoque_opcion_sel
    ON inscripcion_banco_enfoque_opcion (seleccion_id);


-- D.3 · §7.4.2 — objetivos específicos (3 campos).
-- Tabla y no 3 columnas: el orden importa para reproducir el formato IDRD,
-- y el CHECK deja escrito en la BD que son exactamente 3 posiciones.
CREATE TABLE IF NOT EXISTS inscripcion_banco_objetivo_especifico (
    id             BIGSERIAL PRIMARY KEY,
    inscripcion_id BIGINT   NOT NULL
                   REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    orden          SMALLINT NOT NULL,
    texto          TEXT     NOT NULL,
    CONSTRAINT ck_insc_banco_objetivo_orden CHECK (orden BETWEEN 1 AND 3),
    CONSTRAINT uq_insc_banco_objetivo UNIQUE (inscripcion_id, orden)
);


-- D.4 · §8.2 — actividades y descripción.
-- Es la tabla raíz de la Sección 8: el cronograma (§8.3) y el presupuesto
-- (§8.5) cuelgan de la actividad, tal como pide el formato del IDRD
-- ("Actividad Asociada" es una columna del presupuesto).
CREATE TABLE IF NOT EXISTS inscripcion_banco_actividad (
    id             BIGSERIAL PRIMARY KEY,
    inscripcion_id BIGINT   NOT NULL
                   REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    orden          SMALLINT NOT NULL,
    nombre         VARCHAR(200) NOT NULL,
    descripcion    TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_insc_banco_actividad_orden CHECK (orden >= 1),
    CONSTRAINT uq_insc_banco_actividad UNIQUE (inscripcion_id, orden)
);
CREATE INDEX IF NOT EXISTS idx_insc_banco_actividad_insc
    ON inscripcion_banco_actividad (inscripcion_id);


-- D.5 · §8.3 — cronograma matricial (Mes 1-4 × Semana 1-4).
-- Una fila por celda marcada. Modelarlo como 16 columnas booleanas o como
-- un bitmask haría imposible consultar "qué pasa en la semana 3 del mes 2"
-- sin parsear; así es una query normal.
CREATE TABLE IF NOT EXISTS inscripcion_banco_cronograma (
    id           BIGSERIAL PRIMARY KEY,
    actividad_id BIGINT   NOT NULL
                 REFERENCES inscripcion_banco_actividad(id) ON DELETE CASCADE,
    mes          SMALLINT NOT NULL,
    semana       SMALLINT NOT NULL,
    CONSTRAINT ck_insc_banco_cronograma_mes    CHECK (mes BETWEEN 1 AND 4),
    CONSTRAINT ck_insc_banco_cronograma_semana CHECK (semana BETWEEN 1 AND 4),
    CONSTRAINT uq_insc_banco_cronograma UNIQUE (actividad_id, mes, semana)
);
CREATE INDEX IF NOT EXISTS idx_insc_banco_cronograma_act
    ON inscripcion_banco_cronograma (actividad_id);


-- D.6 · §8.4 — equipo de trabajo (filas dinámicas).
-- `nivel_formacion_codigo` reusa el catálogo `nivel_educativo` (al que este
-- mismo script le agrega "Saberes Empíricos / Líder Comunitario"), en vez de
-- abrir un catálogo paralelo con las mismas etiquetas.
--
-- OJO habeas data: acá van nombres de personas reales. Nada de esta tabla
-- se copia a tests, fixtures ni documentación — el repo es público.
CREATE TABLE IF NOT EXISTS inscripcion_banco_equipo (
    id                     BIGSERIAL PRIMARY KEY,
    inscripcion_id         BIGINT   NOT NULL
                           REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    orden                  SMALLINT NOT NULL,
    nombre                 VARCHAR(200) NOT NULL,
    nivel_formacion_codigo INTEGER  REFERENCES nivel_educativo(codigo),
    nivel_formacion_otro   VARCHAR(150),
    rol                    VARCHAR(200) NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_insc_banco_equipo_orden CHECK (orden >= 1),
    CONSTRAINT uq_insc_banco_equipo UNIQUE (inscripcion_id, orden)
);
CREATE INDEX IF NOT EXISTS idx_insc_banco_equipo_insc
    ON inscripcion_banco_equipo (inscripcion_id);


-- D.7 · §8.5 — presupuesto.
-- `valor_total` es GENERATED STORED: el documento lo declara "campo
-- calculado de solo lectura" y el frontend lo muestra, pero quien decide es
-- la BD. Si lo calculara el cliente, un POST directo podría radicar
-- cantidad×unitario que no da el total declarado y burlar el tope.
--
-- NUMERIC, nunca float: son pesos colombianos.
CREATE TABLE IF NOT EXISTS inscripcion_banco_presupuesto (
    id                BIGSERIAL PRIMARY KEY,
    inscripcion_id    BIGINT NOT NULL
                      REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    -- Nullable: si el ciudadano borra una actividad, el rubro no se borra en
    -- silencio; queda huérfano y visible para que lo reasigne.
    actividad_id      BIGINT REFERENCES inscripcion_banco_actividad(id) ON DELETE SET NULL,
    orden             SMALLINT NOT NULL,
    descripcion_rubro TEXT     NOT NULL,
    cantidad          NUMERIC(12,2) NOT NULL,
    valor_unitario    NUMERIC(16,2) NOT NULL,
    valor_total       NUMERIC(18,2)
                      GENERATED ALWAYS AS (cantidad * valor_unitario) STORED,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_insc_banco_presupuesto_orden     CHECK (orden >= 1),
    CONSTRAINT ck_insc_banco_presupuesto_cantidad  CHECK (cantidad > 0),
    CONSTRAINT ck_insc_banco_presupuesto_unitario  CHECK (valor_unitario >= 0),
    CONSTRAINT uq_insc_banco_presupuesto UNIQUE (inscripcion_id, orden)
);
CREATE INDEX IF NOT EXISTS idx_insc_banco_presupuesto_insc
    ON inscripcion_banco_presupuesto (inscripcion_id);

-- NOTA sobre el tope presupuestal ($17M / $14M / $11M): NO se modela acá.
-- El documento lo amarra a la POSICIÓN en el ranking, que no existe mientras
-- la convocatoria está abierta (depende de quién se postule después). Es la
-- decisión #2 pendiente de Deportes (§A.5 del plan). Cuando se resuelva, el
-- tope es una regla del servicio de radicación, no una columna.


-- D.8 · §1.4, §1.8 y §1/9 — anexos documentales.
-- Hoy solo hay dos huecos sueltos en la cabecera (`soporte_legal_mongo_id` y
-- `firma_mongo_id`) y el resto se pide como URL pegada a OneDrive. El
-- documento exige que los archivos vivan DENTRO del aplicativo y que al
-- descargar se unifiquen en un consolidado ("Tu Pago"): eso necesita una
-- tabla, no una columna por tipo de documento.
--
-- Mongo sigue siendo el sistema de registro (ya cifrado); `onedrive_item_id`
-- es el espejo legible del Frente B. Acá NO va el contenido del archivo.
CREATE TABLE IF NOT EXISTS inscripcion_banco_anexo (
    id               BIGSERIAL PRIMARY KEY,
    inscripcion_id   BIGINT      NOT NULL
                     REFERENCES inscripcion_banco_iniciativa(id) ON DELETE CASCADE,
    tipo             VARCHAR(40) NOT NULL,
    mongo_id         VARCHAR(64),
    onedrive_item_id VARCHAR(160),
    nombre_archivo   VARCHAR(255),
    mime             VARCHAR(100),
    tamano_bytes     INTEGER,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_insc_banco_anexo_tipo CHECK (tipo IN (
        'soporte_legal',           -- §1.4
        'cedula_representante',    -- §1.8
        'rut',                     -- §1/9
        'reconocimiento_deportivo',-- §1/9
        'aval_sectorial',          -- §1/9
        'firma',                   -- §9
        'complementario',          -- §1/9 genérico
        'consolidado'              -- salida "Tu Pago"
    )),
    -- Un archivo sin custodia no es un anexo.
    CONSTRAINT ck_insc_banco_anexo_custodia
        CHECK (mongo_id IS NOT NULL OR onedrive_item_id IS NOT NULL)
);
-- Los tipos únicos van una sola vez; 'complementario' puede repetirse.
CREATE UNIQUE INDEX IF NOT EXISTS uq_insc_banco_anexo_tipo_unico
    ON inscripcion_banco_anexo (inscripcion_id, tipo)
    WHERE tipo <> 'complementario';

COMMIT;

-- ============================================================================
-- VERIFICACIÓN POST-APLICACIÓN (correr aparte, fuera de la transacción)
-- ============================================================================
-- SELECT count(*) FROM banco_enfoque_familia WHERE seccion='5.2';   -- espera 7
-- SELECT count(*) FROM banco_enfoque_familia WHERE seccion='7.8';   -- espera 11
-- SELECT count(*) FROM banco_enfoque_opcion;                        -- espera 59 (27 de §5.2 + 32 de §7.8)
-- SELECT count(*) FROM modalidad_recreodeportiva;                   -- espera 5
-- SELECT count(*) FROM instancia_concertacion;                      -- espera 5
-- SELECT count(*) FROM rango_experiencia WHERE activo;              -- espera 5
-- SELECT count(*) FROM rango_poblacion_atendida WHERE activo;       -- espera 4
-- SELECT count(*) FROM inscripcion_banco_iniciativa;                -- espera 24 (sin cambios)
