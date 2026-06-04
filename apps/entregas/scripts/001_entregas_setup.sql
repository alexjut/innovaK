-- ============================================================================
-- ENTREGA de insumos/utensilios — captura de beneficiarios (tipo_evento ENTREGA)
-- Espeja entrega_beca (que ya funciona en producción). PKs BIGSERIAL (S5 cerrada).
-- NO aplicar sin backup < 24h + confirmación de Alex.
-- ============================================================================

-- Cabecera: a quién se le entregó (persona) + firma. Una fila por beneficiario.
CREATE TABLE IF NOT EXISTS entrega_insumo (
    id                BIGSERIAL PRIMARY KEY,
    evento_id         INTEGER NOT NULL REFERENCES evento(id),
    persona_id        INTEGER REFERENCES persona(id),
    tipo_doc_codigo   INTEGER,
    numero_documento  VARCHAR(40) NOT NULL,
    nombre1           VARCHAR(80) NOT NULL,
    nombre2           VARCHAR(80),
    apellido1         VARCHAR(80) NOT NULL,
    apellido2         VARCHAR(80),
    telefono          VARCHAR(40),
    correo            VARCHAR(160),
    direccion         TEXT,
    barrio_codigo     VARCHAR(20),
    upl_codigo        SMALLINT,
    firma_imagen_url  TEXT,
    firma_mongo_id    VARCHAR(64),
    firma_fecha       DATE,
    estado            VARCHAR(20) NOT NULL DEFAULT 'enviada',  -- enviada|validada|rechazada
    observaciones     TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_entrega_insumo_evento_doc UNIQUE (evento_id, numero_documento)
);
CREATE INDEX IF NOT EXISTS idx_entrega_insumo_evento  ON entrega_insumo(evento_id);
CREATE INDEX IF NOT EXISTS idx_entrega_insumo_persona ON entrega_insumo(persona_id);
CREATE INDEX IF NOT EXISTS idx_entrega_insumo_estado  ON entrega_insumo(estado);

-- Puente con cantidad: qué insumo(s) del catálogo `implemento` y cuántos.
CREATE TABLE IF NOT EXISTS entrega_insumo_elemento (
    id                BIGSERIAL UNIQUE,
    entrega_id        BIGINT NOT NULL REFERENCES entrega_insumo(id) ON DELETE CASCADE,
    implemento_codigo SMALLINT NOT NULL REFERENCES implemento(codigo),
    cantidad          INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (entrega_id, implemento_codigo)
);
