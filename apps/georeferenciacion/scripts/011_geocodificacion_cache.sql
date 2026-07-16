-- 011 — Caché de geocodificación (Fase 0 del plan del mapa)
--
-- Contexto: `services/geocoder.py` resuelve dirección → punto contra la capa
-- oficial de placas domiciliarias de Catastro. Esa capa tiene **1.772.936**
-- puntos (376.986 solo en el bbox de Kennedy) y nosotros consultamos ~280 — la
-- meta del proyecto 2784. Sincronizarla en bloque sería bajar 1.346 placas por
-- cada una que usamos. Regla que seguimos: **se sincroniza lo que se consume
-- entero, se cachea lo que se consulta por clave.**
--
-- QUÉ GUARDA Y QUÉ NO
--   Guarda DÓNDE está la dirección (punto). Un edificio no se mueve: se cachea
--   para siempre, sin TTL.
--   NO guarda el estrato. El estrato se resuelve local en cada corrida contra
--   `manzana_estrato` (que sí sincronizamos). Así, si Catastro re-estratifica,
--   el próximo sync lo trae y los puntos cacheados dan el estrato nuevo — sin
--   volver a geocodificar nada.
--
-- Se cachean también los NEGATIVOS (sin_hit / fuera_kennedy / no_parseable): si
-- no, cada corrida vuelve a preguntarle a Catastro por las que ya sabemos que no
-- resuelven. `consultado_at` permite reintentarlas a propósito
-- (`--refrescar-fallidos`) por si Catastro agrega la dirección después.
--
-- Tabla nueva y aislada: no toca ninguna existente. Reconstruible — si se pierde,
-- se vuelve a llenar consultando Catastro.
--
-- Aplicar:  docker exec innova_k python -c "from django.db import connection; \
--             connection.cursor().execute(open('apps/georeferenciacion/scripts/011_geocodificacion_cache.sql').read())"
--           (el contenedor NO trae psql — ver bitácora 2026-06-04)
-- Backup previo requerido (<24h): poblacion_kennedy_diario.dump 2026-07-16 02:00 ✅
-- Rollback: 011_geocodificacion_cache_rollback.sql

BEGIN;

CREATE TABLE IF NOT EXISTS geocodificacion_cache (
    id              BIGSERIAL PRIMARY KEY,

    -- Clave: la dirección NORMALIZADA (salida de geocoder._normalizar).
    -- Deduplica variantes de mayúsculas/espacios/abreviaturas: "cra 78 m #39-20 sur"
    -- y "CRA 78M # 39-20 SUR" son la misma consulta.
    direccion_norm  TEXT NOT NULL,
    -- Lo que escribió la persona, tal cual. Para auditoría: alimenta un puntaje.
    direccion_raw   TEXT,

    -- Lo que se le preguntó a Catastro (formato oficial: 'KR 78M' + '39 30 S').
    via             TEXT,
    placa           TEXT,

    -- El resultado. NULL cuando no resolvió: no se infiere nada.
    lon             DOUBLE PRECISION,
    lat             DOUBLE PRECISION,

    -- Auditable: cómo se llegó y con cuánta confianza.
    --   placa_exacta | via_mayoria | fuera_kennedy | sin_hit | no_parseable
    metodo          VARCHAR(20) NOT NULL,
    confianza       NUMERIC(3,2),
    fuente          VARCHAR(48) NOT NULL DEFAULT 'catastro:placadomiciliaria',

    consultado_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    hits            INTEGER NOT NULL DEFAULT 0,   -- cuántas veces se reusó

    CONSTRAINT geocodificacion_cache_direccion_norm_key UNIQUE (direccion_norm),
    -- Coherencia: si hay punto tiene que haber lon Y lat.
    CONSTRAINT geocodificacion_cache_punto_completo
        CHECK ((lon IS NULL) = (lat IS NULL))
);

-- Reintentar solo las que fallaron, sin recorrer la tabla entera.
CREATE INDEX IF NOT EXISTS idx_geocodificacion_cache_metodo
    ON geocodificacion_cache (metodo);

COMMENT ON TABLE geocodificacion_cache IS
    'Caché permanente dirección→punto (Catastro placadomiciliaria). No guarda '
    'estrato: eso se resuelve contra manzana_estrato en cada corrida. '
    'Reconstruible. Ver apps/georeferenciacion/services/geocoder.py';

COMMIT;
