-- =====================================================================
-- hub_card — cards top-level del hub, manejadas por DATOS (no hardcode).
-- Decisión Alex 2026-06-18: "las cards del hub no están automatizadas, hay
-- que poder agregarlas como el mapa, sin depender de desarrollo".
-- Cada card se gatea por la intersección de sus `modulos` con los del usuario.
--
-- APLICAR tras backup < 24 h. El contenedor innova_k NO tiene psql:
--   connection.cursor().execute(open('.../004_hub_card.sql').read())
-- Luego: python manage.py seed_hub_cards   (siembra las 7 cards actuales).
-- REVERSA: DROP TABLE hub_card;
-- =====================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS hub_card (
    id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(40) UNIQUE NOT NULL,
    titulo TEXT NOT NULL,
    subtitulo TEXT,
    icono VARCHAR(40),                 -- fontawesome (fa-*), como el hub actual
    color VARCHAR(20),                 -- primary/accent/info/danger/warning/success
    ruta VARCHAR(120) NOT NULL,        -- ruta SPA: /actividades, /festivales…
    modulos TEXT,                      -- CSV de códigos de módulo que dan acceso
    orden SMALLINT NOT NULL DEFAULT 100,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_hub_card_orden ON hub_card(orden);

COMMIT;
-- REVERSA: DROP TABLE IF EXISTS hub_card;
