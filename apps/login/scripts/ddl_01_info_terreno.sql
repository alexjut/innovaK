-- =============================================================================
-- PR1 INFO_TERRENO — DDL
-- Fecha: 2026-04-23
-- Rama: feat/mapa-kennedy-dashboard
-- Autor: alexjut + Claude Code
--
-- OBJETIVO:
-- Tabla 1:1 con evento para campos específicos del tipo INFO_TERRENO
-- (salida a terreno con confirmación GPS + fotos).
--
-- DECISIONES DE DISEÑO:
-- - NO se toca tabla tipo_archivo (solo tiene id, nombre — sin columna
--   codigo). El tipo 'Foto de evidencia de visita en terreno' se crea
--   on-demand desde la view con get_or_create(nombre=...).
-- - FK ON DELETE CASCADE: si el evento se borra, sus datos de terreno
--   también (1:1 estricto).
--
-- PRE-REQUISITOS:
-- - Backup pre-PR1 confirmado: poblacion_kennedy_pre_pr1_20260423_*.dump
--
-- ROLLBACK:
--   DROP TABLE IF EXISTS evento_info_terreno;
-- =============================================================================

BEGIN;

CREATE TABLE evento_info_terreno (
    evento_id         INTEGER PRIMARY KEY REFERENCES evento(id) ON DELETE CASCADE,

    -- Campos de planeación (se llenan al crear el evento)
    hallazgos         TEXT,
    recorrido         TEXT,
    observaciones     TEXT,

    -- Confirmación en terreno (desde QR del funcionario + GPS del navegador)
    lat_confirmacion  NUMERIC(9, 6),
    lon_confirmacion  NUMERIC(9, 6),
    timestamp_llegada TIMESTAMPTZ,
    confirmado        BOOLEAN DEFAULT FALSE,

    created_at        TIMESTAMPTZ DEFAULT now(),
    updated_at        TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE  evento_info_terreno                    IS 'Datos específicos para eventos tipo INFO_TERRENO. 1:1 con evento.';
COMMENT ON COLUMN evento_info_terreno.confirmado         IS 'True cuando el funcionario escanea su QR en terreno y comparte GPS + fotos';
COMMENT ON COLUMN evento_info_terreno.timestamp_llegada  IS 'Momento exacto en que el funcionario confirmó llegada vía QR + GPS';

COMMIT;
