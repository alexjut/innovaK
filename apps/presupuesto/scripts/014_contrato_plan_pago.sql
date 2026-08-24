-- 014_contrato_plan_pago.sql — el plan de pago que captura el área.
--
-- QUÉ SE BUSCÓ ANTES DE CREAR (2026-08-24): barrido de las 271 tablas por
-- `plan.*pago|programad|desembols|giro|cuota`. Sólo aparece `secop_plan_pago`,
-- que es el espejo de SECOP y es de SOLO LECTURA. No hay dónde guardar el plan
-- de un contrato que SECOP no publica.
--
-- Y hay 5 de 25 así. Educación es uno: el CIA 773/2025 no tiene una sola fila
-- en SECOP, así que su plan de pago no existe en ninguna parte.
--
-- ─── LA DECISIÓN QUE MÁS IMPORTA: ESTA TABLA NO COPIA A SECOP ───
--
-- Los 4.887 contratos que SECOP sí publica NO se replican acá. El servicio lee
-- las dos fuentes y muestra la oficial cuando existe. Copiarlas habría creado
-- dos versiones del mismo plan que se separan en la primera actualización del
-- cron — y arreglar eso después cuesta mucho más que no hacerlo.
--
-- Acá vive SÓLO lo que el área captura porque la fuente no lo trae.
--
-- ─── POR QUÉ `periodo` ES TEXTO Y NO UN TRIMESTRE ───
--
-- El plan §17 lo pide explícito: no asumir cuatro trimestres. Un contrato paga
-- mensual, otro por hitos de obra, otro contra entrega, otro con anticipo y
-- saldo. Con una etiqueta libre caben los cuatro:
--
--     «Enero 2026»   «Hito 1 — entrega de estudios»   «Anticipo 30 %»
--
-- El ORDEN va aparte, en su propia columna: es lo que ordena el plan, no el
-- texto de la etiqueta. Ordenar por texto pondría «Abril» antes que «Enero».
--
-- ADITIVA: crea una tabla nueva. No toca nada existente.

BEGIN;

CREATE TABLE IF NOT EXISTS contrato_plan_pago (
    id            bigserial    PRIMARY KEY,
    contrato_id   integer      NOT NULL REFERENCES contrato(id) ON DELETE CASCADE,

    -- El orden manda; la etiqueta describe. Ver arriba.
    orden         smallint     NOT NULL,
    periodo       varchar(80)  NOT NULL,
    fecha_programada date,

    -- NULL ≠ 0. Un pago programado en cero es un dato («este período no paga»);
    -- NULL es «todavía no se sabe». La distinción se respeta en toda la fase.
    programado    numeric(18, 2),
    pagado        numeric(18, 2),

    observacion   text,

    -- Rastro. Las tres van juntas, igual que en etapa y forma de pago: lo
    -- escribe una persona sobre información contractual.
    usuario_id    integer,
    created_at    timestamptz  NOT NULL DEFAULT now(),
    updated_at    timestamptz,

    -- Dos filas con el mismo orden en el mismo contrato serían un plan
    -- ambiguo: no se sabría cuál va antes.
    CONSTRAINT contrato_plan_pago_orden_unico UNIQUE (contrato_id, orden)
);

COMMENT ON TABLE contrato_plan_pago IS
    'Plan de pago CAPTURADO por el área. No replica secop_plan_pago: el servicio lee ambas y la oficial manda.';
COMMENT ON COLUMN contrato_plan_pago.periodo IS
    'Etiqueta libre: «Enero 2026», «Hito 1», «Anticipo 30%». No se asume periodicidad.';
COMMENT ON COLUMN contrato_plan_pago.programado IS
    'NULL = no se sabe. 0 = este período no paga. No son lo mismo.';

CREATE INDEX IF NOT EXISTS idx_contrato_plan_pago_contrato
    ON contrato_plan_pago (contrato_id, orden);

COMMIT;
