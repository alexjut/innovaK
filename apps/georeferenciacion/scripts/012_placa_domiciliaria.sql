-- Capa de placas domiciliarias de Catastro Bogotá, local.
--
-- POR QUÉ LOCAL (y no consultando a Catastro en vivo):
--   El 2026-07-16 se midió el servicio `catastro/placadomiciliaria` para
--   autocompletar direcciones. La MISMA consulta, 6 veces seguidas:
--     1 devolvió 20 resultados en 6,6 s · 5 devolvieron VACÍO en 1,8 s, sin error.
--   Y un COUNT acotado al bbox de Kennedy se cayó por timeout a los 60 s.
--   Un autocompletar sobre eso le diría al ciudadano "esa dirección no existe"
--   5 de cada 6 veces: una respuesta equivocada que se ve convincente. Con la
--   capa local la consulta es <10 ms y siempre da lo mismo.
--
-- POR QUÉ TODA BOGOTÁ y no solo Kennedy:
--   Para poder responder "esa dirección existe, pero queda en Fontibón" en vez
--   de "no existe". Es el caso real de las organizaciones que declaran un barrio
--   de Kennedy y tienen la sede en otra localidad (4 de 24 en el piloto).
--   `en_kennedy` se precalcula al sincronizar (point-in-polygon contra el
--   contorno) para que el autocompletar filtre por índice y solo caiga al resto
--   de la ciudad si no hay nada acá.
--
-- Tamaño esperado: ~1.772.936 filas (~150 MB tabla + ~150 MB índices).
-- Reconstruible: es una copia de una fuente pública. Si se pierde, se re-sincroniza.
--
-- Aplicar con backup < 24 h. Rollback en 012_placa_domiciliaria_rollback.sql.

BEGIN;

CREATE TABLE IF NOT EXISTS placa_domiciliaria (
    -- Clave natural de Catastro: hace el upsert idempotente y permite
    -- re-sincronizar por lotes sin duplicar ni borrar la tabla.
    objectid        BIGINT PRIMARY KEY,
    via             TEXT NOT NULL,              -- PDONVIAL: 'CL 42F S'
    placa           TEXT NOT NULL,              -- PDOTEXTO: '72K 10'
    lon             DOUBLE PRECISION NOT NULL,
    lat             DOUBLE PRECISION NOT NULL,
    en_kennedy      BOOLEAN NOT NULL DEFAULT FALSE,
    sincronizado_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT placa_domiciliaria_lonlat_bogota
        CHECK (lon BETWEEN -74.6 AND -73.9 AND lat BETWEEN 3.7 AND 4.9)
);

-- El autocompletar hace `via LIKE 'CL 42%'`. En una BD con locale distinto de C,
-- un índice B-tree normal NO se usa para LIKE por prefijo: hace falta
-- `text_pattern_ops`. Sin esto son 3 seek-scans sobre 1,77 M de filas.

-- Modo 1 — sugerir vías dentro de Kennedy (el 99 % de las pulsaciones).
CREATE INDEX IF NOT EXISTS idx_placa_via_kennedy
    ON placa_domiciliaria (via text_pattern_ops) WHERE en_kennedy;

-- Modo 2 — vía exacta + placa por prefijo.
CREATE INDEX IF NOT EXISTS idx_placa_via_placa
    ON placa_domiciliaria (via, placa text_pattern_ops);

-- Respaldo — "existe, pero está en otra localidad".
CREATE INDEX IF NOT EXISTS idx_placa_via
    ON placa_domiciliaria (via text_pattern_ops);

COMMIT;
