-- =====================================================================
-- Tabla espejo SOLO-LECTURA de Planeación (SEGPLAN / Datos Abiertos SDP-PDL).
-- Fuente: DatosAbiertosProyectosDesarrolloLocal.csv (mapa-inversiones), filtrada
-- a Kennedy. Grano = proyecto × meta × actividad × vigencia (el mismo del visor).
-- Cruza contra lo interno por codigo_proyecto (normalizado sin ceros) ⇄ proyecto.codigo
-- y por plan_meta_producto_id (SEGPLAN) ⇄ metas.codigo_meta.
--
-- ⚠️ NO APLICADO. Requiere OK de Alex + backup < 24 h. El contenedor no trae psql:
--    aplicar vía connection.cursor(). REVERSA al final.
-- =====================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS sdp_meta_oficial (
    id                      BIGSERIAL PRIMARY KEY,
    vigencia                SMALLINT      NOT NULL,          -- año (col Vigencia)
    -- Proyecto (nivel macro)
    codigo_proyecto         VARCHAR(20)   NOT NULL,          -- normalizado ⇄ proyecto.codigo
    codigo_bpin             VARCHAR(30),
    nombre_proyecto         TEXT,
    estado_proyecto         VARCHAR(40),
    id_localidad            VARCHAR(4)    NOT NULL DEFAULT '08',
    localidad               VARCHAR(80),
    sector                  VARCHAR(120),
    total_programado        NUMERIC(20,2),
    total_comprometido      NUMERIC(20,2),
    total_girado            NUMERIC(20,2),
    -- Meta (SEGPLAN)
    plan_meta_producto_id   VARCHAR(20)   NOT NULL,          -- ⇄ metas.codigo_meta
    plan_meta_producto_nombre TEXT,
    -- Actividad / anualización
    actividad_codigo        VARCHAR(20)   NOT NULL DEFAULT '',
    actividad_nombre        TEXT,
    tipo_anualizacion       VARCHAR(20),                     -- Suma | Constante
    -- Magnitudes (avance físico)
    magnitud_programada     NUMERIC(20,4),
    magnitud_comprometida   NUMERIC(20,4),
    magnitud_entregada      NUMERIC(20,4),
    pct_comprometido        NUMERIC(9,4),
    pct_entregado           NUMERIC(9,4),
    -- Valores ($)
    valor_programado        NUMERIC(20,2),
    valor_comprometido      NUMERIC(20,2),
    valor_girado            NUMERIC(20,2),
    avance_financiero       NUMERIC(9,4),
    -- Trazabilidad de ingesta
    fuente                  VARCHAR(80)   NOT NULL DEFAULT 'DatosAbiertosProyectosDesarrolloLocal',
    hash_fila               CHAR(64),
    ingerido_en             TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT uq_sdp_meta UNIQUE (vigencia, codigo_proyecto, plan_meta_producto_id, actividad_codigo)
);
CREATE INDEX IF NOT EXISTS idx_sdp_meta_proy    ON sdp_meta_oficial (codigo_proyecto);
CREATE INDEX IF NOT EXISTS idx_sdp_meta_metacod ON sdp_meta_oficial (plan_meta_producto_id);
CREATE INDEX IF NOT EXISTS idx_sdp_meta_vig     ON sdp_meta_oficial (vigencia);

COMMIT;

-- =====================================================================
-- REVERSA:  DROP TABLE IF EXISTS sdp_meta_oficial;
-- =====================================================================
