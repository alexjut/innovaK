-- =====================================================================
-- Caracterización SEGURIDAD — tabla dedicada (decisión Alex: todo a tablas
-- dedicadas, Seguridad sector 7). Sector seguridad y convivencia.
-- Aplicar tras backup < 24 h. REVERSA al final.
-- =====================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS caracterizacion_seguridad (
    id BIGSERIAL PRIMARY KEY,
    persona_id INTEGER NOT NULL REFERENCES persona(id),
    evento_id INTEGER REFERENCES evento(id) ON DELETE SET NULL,
    funcionario_id INTEGER,
    -- Caracterización de seguridad / convivencia
    percepcion_seguridad VARCHAR(10),          -- alta | media | baja
    fue_victima BOOLEAN,                        -- ¿ha sido víctima de un hecho?
    tipo_hecho VARCHAR(30),                     -- hurto | rina | violencia_intrafamiliar | otro
    denuncio BOOLEAN,                           -- ¿lo denunció?
    pertenece_frente BOOLEAN,                   -- ¿pertenece a frente/red de seguridad?
    observaciones TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_caract_seguridad_persona ON caracterizacion_seguridad(persona_id);
CREATE INDEX IF NOT EXISTS idx_caract_seguridad_evento  ON caracterizacion_seguridad(evento_id);

COMMIT;

-- =====================================================================
-- REVERSA:  DROP TABLE IF EXISTS caracterizacion_seguridad;
-- =====================================================================
