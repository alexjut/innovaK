-- 020 · Presupuesto por meta y vigencia — el hueco de la APROPIACIÓN
--
-- POR QUÉ. El cockpit muestra hoy «Programado», y esa cifra es —medido, 93 %
-- de 70 metas dentro del 5 %— el «Presupuesto proyectado PDL Total» del
-- cuatrienio: la meta ASPIRACIONAL. El primer paso real de ejecución es la
-- «Apropiación POAI inicial», que es la que de verdad se asigna para ejecutar
-- en la vigencia y puede ser mayor o menor que la proyectada (medido: la meta
-- 23772 en 2025 proyecta $3.261.800.000 y apropia $3.751.341.000, un 15 % más).
-- La cadena correcta para un «% de ejecución» es
--     Apropiación → Comprometido → Girado
-- y no Proyectado → Comprometido → Girado.
--
-- Esas cuatro columnas llegan por vigencia en la Matriz PDL que manda la ALK,
-- y hoy NO tienen dónde guardarse: ninguna tabla de la base tiene columna de
-- apropiación (verificado contra information_schema).
--
-- POR QUÉ UNA TABLA NUEVA Y NO `sdp_meta_oficial`. Ya se intentó y se revirtió
-- el mismo día. El UNIQUE real de esa tabla es (vigencia, proyecto, indicador)
-- **SIN `fuente`**, así que insertar ahí no agrega una fuente en paralelo:
-- PISA la fila oficial. Rompió 10 tests de apps.dashboard que suman
-- total_programado/valor_programado esperando una sola fuente.
--
-- Por eso acá `fuente` va DENTRO del UNIQUE: la matriz de la ALK y cualquier
-- fuente futura conviven sin pisarse, y siempre se sabe de dónde salió cada
-- cifra. Es la lección de aquel incidente, escrita en el schema.
--
-- ADITIVO: crea una tabla nueva y no toca ninguna existente. Rollback en
-- rollback_020_presupuesto_meta_vigencia.sql (un DROP).

BEGIN;

CREATE TABLE IF NOT EXISTS presu_presupuesto_meta_vigencia (
    id               BIGSERIAL PRIMARY KEY,

    -- Se engancha por el código SEGPLAN (metas.codigo_meta = el
    -- plan_meta_producto_id del espejo oficial). Se guarda el código y no un
    -- FK duro porque la matriz puede traer metas que todavía no existan como
    -- fila interna: la cifra no se pierde mientras se resuelve el enganche.
    codigo_meta      VARCHAR(20)  NOT NULL,
    proyecto_codigo  INTEGER,

    vigencia         SMALLINT     NOT NULL,

    -- Las cuatro columnas de plata, en PESOS (no en millones: el Excel las
    -- trae en pesos y convertir de ida y vuelta es donde se pierden cifras).
    proyectado_pdl   NUMERIC(18,2),
    apropiacion_poai NUMERIC(18,2),
    comprometido     NUMERIC(18,2),
    girado           NUMERIC(18,2),

    fuente           VARCHAR(30)  NOT NULL DEFAULT 'matriz_pdl_alk',
    archivo_origen   VARCHAR(255),
    cargado_por_id   INTEGER,

    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),

    -- `fuente` va DENTRO del UNIQUE. Ver el encabezado: es exactamente lo que
    -- le faltaba a sdp_meta_oficial y lo que hizo que espejar ahí pisara la
    -- fila oficial en vez de agregar una fuente en paralelo.
    CONSTRAINT uq_presup_meta_vigencia_fuente
        UNIQUE (codigo_meta, vigencia, fuente)
);

CREATE INDEX IF NOT EXISTS idx_presup_meta_vig_meta
    ON presu_presupuesto_meta_vigencia (codigo_meta);
CREATE INDEX IF NOT EXISTS idx_presup_meta_vig_vigencia
    ON presu_presupuesto_meta_vigencia (vigencia);
CREATE INDEX IF NOT EXISTS idx_presup_meta_vig_proyecto
    ON presu_presupuesto_meta_vigencia (proyecto_codigo);

COMMENT ON TABLE presu_presupuesto_meta_vigencia IS
    'Presupuesto por meta SEGPLAN y vigencia (proyectado PDL / apropiacion POAI / '
    'comprometido / girado). Fuente declarada y dentro del UNIQUE para que varias '
    'fuentes convivan sin pisarse. Se carga con importar_matriz_pdl_alk.';
COMMENT ON COLUMN presu_presupuesto_meta_vigencia.apropiacion_poai IS
    'Apropiacion POAI inicial: lo que de verdad se asigna para ejecutar en la '
    'vigencia. Es el primer eslabon de Apropiacion -> Comprometido -> Girado, '
    'NO el proyectado PDL, que es la meta aspiracional del cuatrienio.';

COMMIT;
