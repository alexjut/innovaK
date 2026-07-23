-- =====================================================================
-- Tabla espejo SOLO-LECTURA de SECOP II — Contratos ADJUDICADOS de Kennedy.
-- Fuente: API Socrata datos.gov.co dataset jbjy-vk9h (SECOP II - Contratos
-- Electrónicos), filtrada a nombre_entidad='ALCALDIA LOCAL DE KENNEDY' y
-- excluyendo Borrador/Cancelado (adjudicados). Es la "lista general de contratos"
-- oficial; se enlaza a lo interno por referencia_del_contrato / numero.
--
-- ⚠️ NO APLICADO. Requiere OK de Alex + backup < 24 h. Aplicar vía
--    connection.cursor(). REVERSA al final.
-- =====================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS secop_contrato (
    id                      BIGSERIAL PRIMARY KEY,
    id_contrato             VARCHAR(60)  NOT NULL,           -- PK natural de SECOP
    referencia_contrato     VARCHAR(80),                     -- ⇄ contrato.contrato_numero (enlace interno)
    proceso_de_compra       VARCHAR(80),
    anio                    SMALLINT,
    estado_contrato         VARCHAR(40),
    tipo_contrato           VARCHAR(80),
    modalidad               VARCHAR(120),
    descripcion_proceso     TEXT,
    objeto_contrato         TEXT,
    proveedor               TEXT,
    documento_proveedor     VARCHAR(40),
    valor_contrato          NUMERIC(20,2),
    valor_pagado            NUMERIC(20,2),
    valor_pendiente_ejec    NUMERIC(20,2),
    saldo_cdp               NUMERIC(20,2),
    fecha_firma             DATE,
    fecha_inicio            DATE,
    fecha_fin               DATE,
    url_proceso             TEXT,
    nombre_entidad          VARCHAR(160),
    nit_entidad             VARCHAR(30),
    -- Trazabilidad
    fuente                  VARCHAR(60)  NOT NULL DEFAULT 'SECOP_II_jbjy-vk9h',
    hash_fila               CHAR(64),
    ingerido_en             TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_secop_contrato UNIQUE (id_contrato)
);
CREATE INDEX IF NOT EXISTS idx_secop_ref    ON secop_contrato (referencia_contrato);
CREATE INDEX IF NOT EXISTS idx_secop_estado ON secop_contrato (estado_contrato);
CREATE INDEX IF NOT EXISTS idx_secop_anio   ON secop_contrato (anio);

COMMIT;

-- =====================================================================
-- REVERSA:  DROP TABLE IF EXISTS secop_contrato;
-- =====================================================================
