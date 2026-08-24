-- =====================================================================
-- 011_secop_plan_pago.sql — espejo SOLO-LECTURA del PLAN DE PAGOS de
-- SECOP II (datos.gov.co, recurso `uymx-8p3j`), filtrado a
-- nombre_entidad='ALCALDIA LOCAL DE KENNEDY'.
--
-- ⚠️ ESTADO REAL: **APLICADO el 2026-08-23 (~23:55)**, y NO por la sesión que
--    escribió este script — que lo dejó deliberadamente sin ejecutar porque el
--    DDL lo aprueba Alex. Otra sesión concurrente corrió `apply_011` y acto
--    seguido `ingest_secop_plan_pagos --write`, dejando la tabla con las 36.210
--    filas de Kennedy. El dato quedó correcto y verificado (20 de nuestros 25
--    contratos, 154 filas de pago, 1.097 referencias sin parsear guardadas con
--    ref_* en NULL, 0 claves duplicadas), pero **la aprobación no se pidió**.
--    Si Alex no lo avala, la reversa está en rollback_011_secop_plan_pago.sql y
--    no pierde nada: la tabla es un espejo y se vuelve a bajar con el comando.
--
-- POR QUÉ UNA TABLA NUEVA Y NO `crp` (medido 2026-08-23):
--   · `crp` es la vía INTERNA de presupuesto: 48 columnas de Hacienda,
--     hoy con 0 filas, y el modelo Django solo mapea 5 de esas 48.
--     Algún día la llenará Hacienda con SU dato. Meter ahí una fuente
--     externa contaminaría su semántica: nadie podría volver a decir si
--     una fila de `crp` la puso la Alcaldía o la bajamos de internet.
--   · `forma_pago`, `tipo_crp` y `periodo_fiscal` también están en 0.
--   · Así que el plan de pagos va en espejo aparte, exactamente como
--     `secop_contrato` (008): tabla propia, `fuente`, `hash_fila`,
--     `synced_at`, y CERO escritura desde la aplicación.
--
-- FORMA DE LA FUENTE (medida con una llamada real, no supuesta):
--   · 36.210 filas para Kennedy, 5.046 contratos, $503.633 M.
--   · 33.870 con `fecha_real_de_pago` (estado 'Pagado'); el resto en
--     'Enviado Por Proveedor' 1.307, 'Rechazado' 652, 'Aprobado' 370,
--     'Pendiente Registro' 11.
--   · Cruzado con NUESTROS 25 contratos: 20 tienen plan, 154 filas.
--
-- POR QUÉ EXISTE `secuencia` (medido, no defensivo):
--   La pareja natural (id_del_contrato, id_de_pago) NO es única en la
--   fuente: 36.210 filas dan 36.206 parejas distintas. Son 4 pagos que
--   SECOP publica dos veces, con distinto aprobador y distinta fecha
--   (p. ej. el mismo id_de_pago con `fecha_real_de_pago` en una fila y
--   NULL en la otra). Guardar solo una perdería un dato real de la
--   fuente; sumar las dos DUPLICARÍA la plata. Así que se guardan las
--   dos, numeradas: `secuencia`=0 es la que suma, el resto queda
--   visible y auditable pero fuera de los totales.
--
-- POR QUÉ `ref_tipo/ref_numero/ref_vigencia` SON COLUMNAS:
--   La referencia viene en 62 formatos distintos — 'CPS-033.2023' con
--   PUNTO y 'CPS-1113-2024' con GUION— y 1.097 de 36.210 no parsean con
--   ningún patrón razonable ('CONTRATO DE ARRENDAMIENTO…', el propio
--   'CO1.PCCNTR.…', '###-####'). El parseo se hace UNA vez, en la
--   ingesta, y se persiste: así el cruce con `contrato` es un igual-a
--   entre enteros y no una regexp repetida en cada consulta, y las filas
--   que no parsean quedan con los tres campos en NULL — CONTADAS y
--   guardadas, nunca descartadas en silencio.
-- =====================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS secop_plan_pago (
    id                      BIGSERIAL PRIMARY KEY,

    -- Identidad en la fuente
    id_del_contrato         VARCHAR(60)  NOT NULL,   -- ⇄ secop_contrato.id_contrato
    id_de_pago              VARCHAR(20)  NOT NULL,
    secuencia               SMALLINT     NOT NULL DEFAULT 0,  -- ver nota arriba

    -- Referencia y su parseo (NULL = no parseó; la fila se guarda igual)
    referencia_contrato     VARCHAR(80),
    ref_tipo                VARCHAR(20),
    ref_numero              INTEGER,                 -- ⇄ contrato.contrato_numero
    ref_vigencia            SMALLINT,                -- ⇄ contrato.contrato_vigencia

    -- El pago
    estado                  VARCHAR(40),
    numero_de_factura       TEXT,
    notas                   TEXT,
    valor_a_pagar           NUMERIC(20,2),
    valor_neto              NUMERIC(20,2),
    valor_total             NUMERIC(20,2),

    fecha_de_emision        DATE,
    fecha_de_recepcion      DATE,
    fecha_de_vencimiento    DATE,
    fecha_estimada_de_pago  DATE,
    fecha_real_de_pago      DATE,
    fecha_inicio_contrato   DATE,

    aprobado_por            TEXT,
    compromiso_presupuestal VARCHAR(60),
    nombre_proveedor        TEXT,
    documento_proveedor     VARCHAR(40),
    nombre_entidad          VARCHAR(160),
    nit_entidad             VARCHAR(30),

    -- Trazabilidad (idéntica a `secop_contrato`, C3: `synced_at`)
    fuente                  VARCHAR(60)  NOT NULL DEFAULT 'SECOP_II_uymx-8p3j',
    hash_fila               CHAR(64),
    synced_at               TIMESTAMPTZ  NOT NULL DEFAULT now(),

    CONSTRAINT uq_secop_plan_pago UNIQUE (id_del_contrato, id_de_pago, secuencia)
);

-- El cruce con `contrato` es por (ref_numero, ref_vigencia): índice compuesto.
CREATE INDEX IF NOT EXISTS idx_plan_pago_ref
    ON secop_plan_pago (ref_numero, ref_vigencia);
CREATE INDEX IF NOT EXISTS idx_plan_pago_contrato
    ON secop_plan_pago (id_del_contrato);
CREATE INDEX IF NOT EXISTS idx_plan_pago_estado
    ON secop_plan_pago (estado);

COMMIT;
