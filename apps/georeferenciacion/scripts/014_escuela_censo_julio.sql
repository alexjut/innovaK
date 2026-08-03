-- ============================================================================
-- Escuelas — censo julio 2026: reconciliación, baja lógica y barrio resuelto
-- Fecha: 2026-07-30 · Plan: docs/propuestas/mapa_escuelas_2026-07-30.md
--
-- QUÉ HACE
--   Agrega a `escuela` las columnas que necesita la reconciliación con el censo
--   de julio y la resolución de barrio/UPZ por geometría. NO carga datos: eso
--   lo hace el management command, en otra corrida y con backup previo.
--
-- QUÉ *NO* HACE
--   · NO borra ni una fila. Las escuelas que no vienen en el censo de julio se
--     marcan `estado='inactivo'` con su motivo y fecha, y se revierten con un
--     UPDATE. Decisión de Alex: "nada de DELETE".
--   · NO toca `barrio_codigo`, que ya existe. El barrio resuelto por geometría
--     va en columnas nuevas para poder COMPARAR lo declarado contra lo
--     geométrico; pisar la que ya está borraría la evidencia de la discrepancia,
--     que es justo lo que se quiere auditar.
--
-- TODAS las columnas son NULLABLE y SIN DEFAULT. En PostgreSQL 16 eso hace que
-- el ALTER sea metadata-only: no reescribe las 241 filas ni toma lock de
-- escritura más allá del instante del catálogo. (Un DEFAULT volátil sí forzaría
-- la reescritura; por eso no hay ninguno.)
--
-- ⚠️ Lo revisa y lo aprueba Alex, con backup previo.
--    Rollback en 014_escuela_censo_julio_rollback.sql
-- ============================================================================

BEGIN;

-- ── A. Ciclo de vida del registro ──────────────────────────────────────────
-- `activo` (boolean) ya existe, pero no dice POR QUÉ ni CUÁNDO se dio de baja.
-- Sin eso, en seis meses nadie sabe si una escuela desapareció porque cerró,
-- porque el área no la reportó, o porque alguien se equivocó cargando.
ALTER TABLE escuela
    ADD COLUMN IF NOT EXISTS estado       VARCHAR(12),
    ADD COLUMN IF NOT EXISTS motivo_baja  TEXT,
    ADD COLUMN IF NOT EXISTS fecha_baja   DATE;

-- ── B. Trazabilidad de la dirección ────────────────────────────────────────
-- El censo de julio corrige 34 direcciones efectivas. Se conserva la de abril:
-- en 6 casos la de julio viene VACÍA, y la regla general es que un censo
-- incompleto no es una corrección — nunca se pisa un valor existente con NULL.
ALTER TABLE escuela
    ADD COLUMN IF NOT EXISTS direccion_anterior TEXT;

-- ── C. Barrio y UPZ resueltos por geometría ────────────────────────────────
-- `barrio_declarado` es lo que digitó el área; `barrio_resuelto` es contra qué
-- polígono cayó el punto. Separados a propósito: la gracia es marcar
-- `discrepancia` cuando no coinciden — por ejemplo la misma dirección reportada
-- como Pio XXII y como Urbanización Catania.
ALTER TABLE escuela
    ADD COLUMN IF NOT EXISTS barrio_declarado    TEXT,
    ADD COLUMN IF NOT EXISTS barrio_resuelto     VARCHAR(20),
    ADD COLUMN IF NOT EXISTS barrio_estado       VARCHAR(16),
    ADD COLUMN IF NOT EXISTS upz_resuelta        VARCHAR(10),
    ADD COLUMN IF NOT EXISTS discrepancia        BOOLEAN,
    ADD COLUMN IF NOT EXISTS geolocalizado       BOOLEAN,
    ADD COLUMN IF NOT EXISTS revision_requerida  BOOLEAN,
    ADD COLUMN IF NOT EXISTS revision_detalle    TEXT;

-- ── D. Datos del censo para el popup ───────────────────────────────────────
-- Una sede de Deportes puede tener varias escuelas (27 direcciones repetidas),
-- cada una con su horario, edades y formador. Va como JSONB y no como columnas
-- sueltas porque son de 1 a 5 disciplinas por sede.
--
-- SIN índice GIN: el popup lee el objeto COMPLETO y el mapa no filtra por
-- disciplina (filtra por tipo Cultura/Deporte, que es columna propia). Un GIN
-- acá solo costaría escritura y espacio sin que nadie lo use. Si mañana se
-- agrega un filtro por disciplina, se crea entonces y con CONCURRENTLY.
ALTER TABLE escuela
    ADD COLUMN IF NOT EXISTS actividades   JSONB,
    ADD COLUMN IF NOT EXISTS url_maps      TEXT,
    ADD COLUMN IF NOT EXISTS censo_origen  VARCHAR(30);

-- ── E. Constraints: NOT VALID primero, VALIDATE después ────────────────────
-- Se agregan como NOT VALID para que el ALTER no escanee la tabla y no pueda
-- fallar por dato viejo. El VALIDATE de abajo sí lo revisa, pero ya con la
-- columna creada: si algo no cuadra, falla el VALIDATE —que es barato de
-- deshacer— y no el ADD COLUMN.
--
-- Verificado antes de escribir esto: `estado` NO existía, así que las 241 filas
-- quedan en NULL y ninguna puede violar nada. El VALIDATE debe pasar limpio.
ALTER TABLE escuela DROP CONSTRAINT IF EXISTS ck_escuela_estado;
ALTER TABLE escuela ADD CONSTRAINT ck_escuela_estado
    CHECK (estado IS NULL OR estado IN ('activo', 'inactivo')) NOT VALID;

-- Coherencia: si está inactivo, tiene que decir por qué y desde cuándo.
-- Es la guarda que impide una baja silenciosa.
ALTER TABLE escuela DROP CONSTRAINT IF EXISTS ck_escuela_baja_justificada;
ALTER TABLE escuela ADD CONSTRAINT ck_escuela_baja_justificada
    CHECK (
        estado IS DISTINCT FROM 'inactivo'
        OR (motivo_baja IS NOT NULL AND fecha_baja IS NOT NULL)
    ) NOT VALID;

-- Cuatro razones distintas de "sin barrio". No es lo mismo no poder que no
-- haber intentado, y por eso son literales cerrados y no texto libre:
--     resuelto        → el punto cae dentro de un polígono
--     cercano_80m     → cayó fuera, pero a menos de 80 m del borde (está sobre
--                       la línea; la geometría de IDECA no es exacta al metro)
--     sin_poligono    → no hay polígono contra el cual cruzar (deuda M22)
--     sin_coordenada  → la escuela no tiene punto (los 31 sin dirección)
ALTER TABLE escuela DROP CONSTRAINT IF EXISTS ck_escuela_barrio_estado;
ALTER TABLE escuela ADD CONSTRAINT ck_escuela_barrio_estado
    CHECK (barrio_estado IS NULL OR barrio_estado IN
           ('resuelto', 'cercano_80m', 'sin_poligono', 'sin_coordenada')) NOT VALID;

ALTER TABLE escuela VALIDATE CONSTRAINT ck_escuela_estado;
ALTER TABLE escuela VALIDATE CONSTRAINT ck_escuela_baja_justificada;
ALTER TABLE escuela VALIDATE CONSTRAINT ck_escuela_barrio_estado;

-- ── F. Índices ─────────────────────────────────────────────────────────────
-- B-tree en `estado` y `origen`: los usan todos los reportes de la
-- reconciliación (cuántas de baja, cuántas del censo nuevo).
CREATE INDEX IF NOT EXISTS idx_escuela_estado  ON escuela (estado);
CREATE INDEX IF NOT EXISTS idx_escuela_origen  ON escuela (origen);
CREATE INDEX IF NOT EXISTS idx_escuela_upz_res ON escuela (upz_resuelta);
-- El mapa pinta lo que tiene coordenada, filtrado por tipo.
CREATE INDEX IF NOT EXISTS idx_escuela_pintables
    ON escuela (tipo) WHERE geolocalizado IS TRUE;

COMMIT;

-- ============================================================================
-- G. ESTADO INICIAL — va APARTE, en su propia transacción.
--
-- Esto NO es metadata: es un UPDATE que toca las 241 filas. Se separa del DDL
-- a propósito, para que "agregar las columnas" y "poblarlas" sean dos pasos que
-- se puedan correr y revisar por separado.
-- ============================================================================

BEGIN;
UPDATE escuela SET estado = 'activo' WHERE estado IS NULL;
UPDATE escuela
   SET geolocalizado = (latitud IS NOT NULL AND longitud IS NOT NULL)
 WHERE geolocalizado IS NULL;
COMMIT;
