-- Capas de territorio de Catastro Bogotá: sector catastral y barrio legalizado.
--
-- POR QUÉ EXISTEN (medido 2026-07-16 contra el contorno real de Kennedy):
--   El mapa dibuja hoy 75 de nuestros 325 barrios — los únicos con geometría —
--   y eso cubre el 56 % del territorio. El 44 % restante sale en blanco: la
--   localidad se ve como un queso suizo. Es la deuda M22.
--
--   Se midió qué capa oficial lo cierra, bajando ambas del servicio y cruzándolas
--   contra el contorno:
--     sector_catastral      135 polígonos tocan Kennedy → cubren 95,9 %  ← la buena
--     barrios_legalizados   163 polígonos tocan Kennedy → cubren 21,1 %
--
--   O sea: el que arregla el mapa es el SECTOR CATASTRAL (56 % → 95,9 %).
--   `barrios_legalizados` NO lo arregla, y conviene decirlo claro para que nadie
--   vuelva a intentarlo: son solo los barrios que pasaron por el trámite de
--   legalización, una quinta parte del suelo. Entra igual porque tiene valor
--   propio — saber qué barrios están legalizados, y por cuál acto, es dato de
--   política, no decoración.
--
-- NINGUNA DE LAS DOS RESUELVE M22 PARA EL BANCO.
--   El estrato de una organización lo da el geocodificador contra la placa
--   domiciliaria, no el polígono del barrio. Estas capas son para DIBUJAR.
--
-- Reconstruibles: son copia de una fuente pública. Si se pierden, se re-sincronizan
--   con `python manage.py sync_capa sector_catastral` / `barrios_legalizados`.
--
-- Aplicar con backup < 24 h. Rollback en 013_capas_territorio_rollback.sql.

BEGIN;

-- ── sector_catastral ─────────────────────────────────────────────────────────
-- 1.230 en Bogotá. Cabe entera: recortarla a Kennedy no ahorra nada y rompería
-- el snap del borde (mismo criterio que las demás capas — ver capas.py).

CREATE TABLE IF NOT EXISTS sector_catastral (
    id          BIGSERIAL PRIMARY KEY,

    -- SCACODIGO. TEXT y no INTEGER a propósito: viene como '004622', con ceros
    -- a la izquierda que son parte del código. Guardarlo como número lo
    -- convertiría en 4622 y dejaría de cruzar contra la fuente.
    -- Verificado 2026-07-16: 1.230 filas, 0 nulos, 1.230 distintos → clave
    -- natural sólida para el ON CONFLICT del upsert.
    codigo      TEXT NOT NULL UNIQUE,

    nombre      TEXT,                       -- SCANOMBRE, p. ej. 'BRASIL'
    tipo        SMALLINT,                   -- SCATIPO (entero en la fuente)

    geometry    JSONB NOT NULL,             -- GeoJSON; el sync convierte los rings de Esri
    properties  JSONB,
    fecha_fuente DATE,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- El mapa sirve "los sectores de Kennedy": se filtra por intersección contra el
-- contorno en tiempo de respuesta, pero el listado por nombre sí se busca.
CREATE INDEX IF NOT EXISTS idx_sector_catastral_nombre
    ON sector_catastral (nombre);


-- ── barrio_legalizado ────────────────────────────────────────────────────────
-- 1.709 en Bogotá.

CREATE TABLE IF NOT EXISTS barrio_legalizado (
    -- OBJECTID de Catastro y NO 'CODIGO_ID' como decía la config original.
    -- Verificado 2026-07-16 contra el servicio: CODIGO_ID es NULL en las 1.709
    -- filas — la columna existe pero Catastro nunca la llenó. Con esa clave el
    -- sync descartaba TODA fila en `_transformar` ("sin clave no hay upsert") y
    -- habría dejado la tabla en cero sin lanzar un solo error.
    objectid            BIGINT PRIMARY KEY,

    nombre              TEXT NOT NULL,      -- NOMBRE
    upz_codigo          INTEGER,            -- CODIGO_UPZ (entero en la fuente)

    -- CODIGO_LOCALIDAD. TEXT por lo mismo que `codigo` arriba: viene '05', '08'.
    -- Kennedy es '08'.
    localidad_codigo    TEXT,

    -- El acto administrativo que legalizó el barrio. Es la vigencia real del
    -- dato (capas.py lo explica: el editingInfo del MapServer viene vacío).
    -- Sin esto la capa dice "legalizado" sin poder decir por cuál resolución.
    acto_administrativo TEXT,               -- ACTO_ADMINISTRATIVO, p. ej. 'RES'
    acto_numero         TEXT,               -- NUMERO_ACTO_ADMINISTRATIVO, p. ej. '420'

    geometry            JSONB NOT NULL,
    properties          JSONB,
    fecha_fuente        DATE,
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- Kennedy es localidad '08': el mapa y los reportes filtran por ahí.
CREATE INDEX IF NOT EXISTS idx_barrio_legalizado_localidad
    ON barrio_legalizado (localidad_codigo);

CREATE INDEX IF NOT EXISTS idx_barrio_legalizado_upz
    ON barrio_legalizado (upz_codigo);

COMMIT;
