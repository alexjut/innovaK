-- 023 · Catálogo de SECTOR — un solo vocabulario, el de la Matriz PDL
--
-- POR QUÉ. `metas.sector` es texto libre y hoy guarda DOS vocabularios a la
-- vez. Medido el 2026-09-03 sobre las 78 filas:
--
--     55 filas con el vocabulario de la MATRIZ  ('SEGURIDAD, CONVIVENCIA Y
--        JUSTICIA', 'CULTURA, RECREACIÓN Y DEPORTE', 'EDUCACIÓN'…)
--     23 filas con el vocabulario INTERNO       ('Seguridad', 'Cultura',
--        'Deporte', 'Educación', 'Infraestructura'…)
--
-- Son 20 valores distintos para 13 sectores reales. La causa no es un typo:
-- `importar_matriz_pdl_alk` hace backfill SOLO de columnas NULL y nunca pisa
-- lo ya escrito, así que las 23 filas que ya traían el nombre interno jamás
-- se actualizaron al de la matriz.
--
-- LO QUE COSTABA. `top_sectores_avance()` agrupa por `metas.sector` (GROUP BY
-- m.sector), así que el mismo sector sale partido en dos barras: Educación
-- aparece con 49,7 % en una fila y EDUCACIÓN con 0,0 % en otra, y el ranking
-- premia al sector que quedó dividido. El gráfico miente por partición, no
-- por cálculo.
--
-- LA AUTORIDAD ES LA MATRIZ, DECIDIDO POR ALEX (2026-09-03): «hay que agregar
-- esos sectores; nuestra luz es esa matriz con SEGPLAN». Por eso el catálogo
-- nace con los 13 valores TAL COMO LOS TRAE LA MATRIZ, incluidos los dos
-- compuestos —'AMBIENTE/HÁBITAT' y 'MUJERES/INTEGRACIÓN SOCIAL'—, que NO se
-- pliegan a 'AMBIENTE' ni a 'MUJERES': la fuente dice que son otra cosa.
-- Consecuencia asumida: 'AMBIENTE' y 'AMBIENTE/HÁBITAT' seguirán siendo dos
-- barras en el gráfico. Ya no como defecto, sino por definición de la fuente.
--
-- POR QUÉ UNA TABLA DE ALIAS, Y QUÉ *NO* ENTRA EN ELLA. El alias resuelve «la
-- misma cosa escrita distinto» y es muchos-a-uno. Medido contra la matriz por
-- la llave estable (proyecto, indicador), tres valores internos NO califican:
--
--     'Infraestructura'                  → MOVILIDAD (1) y CULTURA… (1)
--     'CPS y Planta'                     → no es un sector, es tipo de contrato
--     'Relacionamiento Interinstitucional' → no es un sector
--
-- 'Infraestructura' es el caso que cierra la discusión: mapea a DOS sectores
-- oficiales distintos, así que como alias sería una mentira de uno de los dos
-- lados. Esos tres quedan FUERA del catálogo a propósito y se resuelven por
-- la matriz fila por fila (`metas.sector_id`), no por el nombre.
--
-- ADITIVO. Crea dos tablas nuevas y agrega UNA columna nullable a `metas`.
-- `metas.sector` (texto) se queda intacta hasta que los lectores se muden:
-- se borra en una pasada posterior, no acá.
--
-- Rollback en rollback_023_sector_catalogo.sql.

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- El catálogo: 13 sectores, el vocabulario de la matriz
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS presu_sector (
    id              SERIAL PRIMARY KEY,
    nombre_oficial  VARCHAR(120) NOT NULL,
    activo          BOOLEAN      NOT NULL DEFAULT TRUE,

    -- De qué carga salió y cuál lo retiró. La carga NUNCA borra: lo que
    -- desaparece de la matriz se marca inactivo con la carga que lo retiró.
    -- Quedan como enteros sueltos hasta que exista `MatrizPDLCarga`; poner la
    -- FK ahora obligaría a crear esa tabla en el mismo DDL y son dos
    -- decisiones distintas.
    carga_origen_id INTEGER,
    carga_retiro_id INTEGER,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_presu_sector_nombre UNIQUE (nombre_oficial)
);

COMMENT ON TABLE presu_sector IS
    'Catalogo de SECTOR del PDL. El vocabulario es el de la Matriz PDL de la '
    'ALK (mismo identificador que SEGPLAN), no el interno de innovaK. Incluye '
    'los compuestos AMBIENTE/HABITAT y MUJERES/INTEGRACION SOCIAL como '
    'sectores propios: decision de Alex 2026-09-03, la fuente manda.';
COMMENT ON COLUMN presu_sector.carga_retiro_id IS
    'Carga que retiro el sector. La carga nunca borra: marca inactivo.';

-- ─────────────────────────────────────────────────────────────────────────────
-- Los alias: solo «la misma cosa escrita distinto»
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS presu_sector_alias (
    id          SERIAL PRIMARY KEY,
    sector_id   INTEGER      NOT NULL
                REFERENCES presu_sector (id) ON DELETE CASCADE,

    -- `alias` guarda la forma tal como llega (para poder rastrear el origen);
    -- `alias_norm` es la que se compara: mayúsculas, sin tildes, sin espacios
    -- dobles.
    --
    -- La normalización la hace la APLICACIÓN, aunque `unaccent` sí está
    -- instalada en esta base (verificado en pg_extension). El motivo no es
    -- que no se pueda en SQL: es que la misma función tiene que decidir el
    -- empate al sembrar y al ingerir. Con una versión en Python y otra en SQL,
    -- las dos se separan y el alias empieza a resolver distinto según por
    -- dónde entró el dato.
    alias       VARCHAR(120) NOT NULL,
    alias_norm  VARCHAR(120) NOT NULL,

    origen      VARCHAR(40)  NOT NULL DEFAULT 'innovak_interno',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- El UNIQUE va sobre la forma NORMALIZADA: es la que decide el empate.
    -- Y es global, no por sector: si un mismo texto pudiera apuntar a dos
    -- sectores, el alias no resolvería nada. Es justo lo que descalifica a
    -- 'Infraestructura', que mapea a MOVILIDAD y a CULTURA a la vez.
    CONSTRAINT uq_presu_sector_alias_norm UNIQUE (alias_norm)
);

CREATE INDEX IF NOT EXISTS idx_presu_sector_alias_sector
    ON presu_sector_alias (sector_id);

COMMENT ON TABLE presu_sector_alias IS
    'Formas alternativas de escribir UN sector, para resolver la ingesta. '
    'Muchos-a-uno y con UNIQUE global sobre alias_norm: un texto que mapee a '
    'dos sectores no es un alias y queda fuera a proposito.';

-- ─────────────────────────────────────────────────────────────────────────────
-- El enganche en `metas`
-- ─────────────────────────────────────────────────────────────────────────────
-- Nullable a proposito: 2 de las 78 metas (codigos 8 y 10) no tienen
-- `proyecto_codigo` ni `codind`, asi que no cruzan con la matriz por la llave
-- estable y no se les puede asignar sector sin inventarlo. Se quedan en NULL
-- y se ven como «sin sector», que es la verdad.
ALTER TABLE metas
    ADD COLUMN IF NOT EXISTS sector_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_metas_sector'
    ) THEN
        ALTER TABLE metas
            ADD CONSTRAINT fk_metas_sector
            FOREIGN KEY (sector_id) REFERENCES presu_sector (id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_metas_sector_id ON metas (sector_id);

COMMENT ON COLUMN metas.sector_id IS
    'Sector del catalogo presu_sector. Se llena desde la Matriz PDL por la '
    'llave estable (proyecto_codigo, codind) — NUNCA por el texto de '
    'metas.sector, que mezcla dos vocabularios. metas.sector se conserva '
    'hasta que los lectores se muden y se borra en una pasada posterior.';

COMMIT;
