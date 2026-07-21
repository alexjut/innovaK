-- =====================================================================
-- Caracterización PAZ, MEMORIA Y RECONCILIACIÓN — tabla dedicada.
-- Subgrupo Paz · Proyecto 2106. Modelo PLANO por persona (la iniciativa
-- NO es entidad aparte: su nombre/objetivo van como texto por integrante).
--
-- ⚠️ NO APLICADO. Requiere OK explícito de Alex + backup < 24 h de
--    poblacion_kennedy. El contenedor NO trae psql: aplicar vía
--    connection.cursor().execute(open(script).read()). REVERSA al final.
-- =====================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS caracterizacion_paz (
    id BIGSERIAL PRIMARY KEY,
    persona_id INTEGER NOT NULL REFERENCES persona(id),
    evento_id INTEGER REFERENCES evento(id) ON DELETE SET NULL,
    funcionario_id INTEGER,
    -- Identidad temporal (foto de la caracterización)
    fecha_nacimiento DATE,
    -- Demografía por codigo de catálogos oficiales (datos sensibles Ley 1581)
    sexo_codigo INTEGER,                 -- FK lógica → sexo(codigo)
    identidad_genero_codigo INTEGER,     -- FK lógica → identidad_genero(codigo)
    orientacion_sexual_codigo INTEGER,   -- FK lógica → orientacion_sexual(codigo)
    grupo_etnico_codigo INTEGER,         -- FK lógica → grupo_etnico(codigo)
    tipo_discapacidad_codigo INTEGER,    -- FK lógica → tipo_discapacidad(codigo)
    grupo_priorizado VARCHAR(10),        -- VCA | PPR | DDHH
    -- Iniciativa (modelo plano: texto por integrante)
    iniciativa_nombre VARCHAR(255),
    iniciativa_objetivo TEXT,
    -- Ubicación (dirección validada con lat/lon — regla del proyecto)
    direccion TEXT,
    latitud NUMERIC(9,6),
    longitud NUMERIC(9,6),
    -- Habeas data
    autorizacion_datos BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_caract_paz_persona ON caracterizacion_paz(persona_id);
CREATE INDEX IF NOT EXISTS idx_caract_paz_evento  ON caracterizacion_paz(evento_id);

COMMIT;

-- =====================================================================
-- REVERSA:  DROP TABLE IF EXISTS caracterizacion_paz;
-- =====================================================================
