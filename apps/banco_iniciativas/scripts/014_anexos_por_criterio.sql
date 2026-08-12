-- 014 · Anexos por criterio del Bloque 1 — Documento Guía (2026-08-10)
--
-- POR QUÉ
-- El Documento Guía condiciona el puntaje del Bloque 1 al cargue del soporte:
-- «Si el sistema detecta una opción puntuable activa sin su correspondiente
-- archivo indexado, el algoritmo congelará el paso y no procesará la
-- calificación del criterio.» Hoy `inscripcion_banco_anexo.tipo` solo admite 8
-- valores y ninguno identifica a cuál criterio respalda, así que la regla no se
-- puede programar: un INSERT con un tipo nuevo lo rechaza el CHECK.
--
-- QUÉ HACE
-- Amplía el CHECK con un tipo por criterio puntuable del Bloque 1, más el
-- certificado de residencia (§1, elegibilidad, no puntúa) y el prefijo de los
-- enfoques de §5.2, que son dinámicos: uno por casilla marcada.
--
-- NO borra ni renombra ningún tipo existente: las 8 opciones actuales siguen
-- válidas. Es puramente aditivo y reversible (ver el _rollback).
--
-- SIN DATOS QUE MIGRAR
-- `inscripcion_banco_anexo` tiene 0 filas (verificado 2026-08-10), así que no
-- hay riesgo de que una fila existente viole el CHECK nuevo.
--
-- APLICAR (requiere OK explícito de Alex + backup < 24 h):
--   docker exec innova_k python -c "
--   import django,os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
--   django.setup()
--   from django.db import connection
--   connection.cursor().execute(open('apps/banco_iniciativas/scripts/014_anexos_por_criterio.sql').read())"
--
-- (el contenedor NO trae `psql`; se aplica por cursor, como el resto)

BEGIN;

ALTER TABLE inscripcion_banco_anexo
    DROP CONSTRAINT IF EXISTS ck_insc_banco_anexo_tipo;

ALTER TABLE inscripcion_banco_anexo
    ADD CONSTRAINT ck_insc_banco_anexo_tipo CHECK (
        tipo IN (
            -- ── Ya existentes (§1, §9) ─────────────────────────────────
            'soporte_legal',
            'cedula_representante',
            'rut',
            'reconocimiento_deportivo',
            'aval_sectorial',
            'firma',
            'complementario',
            'consolidado',

            -- ── §1 · elegibilidad territorial (NO puntúa) ──────────────
            -- Certificado de residencia del representante o recibo de
            -- servicio público de Kennedy.
            'residencia_representante',

            -- ── Criterio 1 · Capacidad organizativa (12 pts) ───────────
            'staff_listado',            -- §3.1 listado con firmas
            'trayectoria',              -- §3.2 certificaciones JAC/entidades
            'composicion_genero',       -- §3.3 acta de dignatarios/estatutos
            'beneficiarios_listado',    -- §3.4 planillas o registro fechado

            -- ── Criterio 2 · Arraigo territorial (4 pts) ───────────────
            -- Autorización de uso (JAC/IDRD) + recibo que acredita el estrato.
            'arraigo_uso_espacio',

            -- ── Criterio 3 · Inclusión rango etario (4 pts) ────────────
            'caracterizacion_demografica',   -- §5.1

            -- ── Criterio 5 · Incidencia ciudadana (2 pts) ──────────────
            'instancias_actas',              -- §6.1

            -- ── Criterio 6 · Democratización del fomento (2 pts) ───────
            'declaracion_antecedentes'       -- §6.2 declaración juramentada
        )
        -- ── Criterio 4 · Enfoques poblacionales §5.2 (6 pts) ───────────
        -- Es DINÁMICO: el documento pide «un cajón de cargue por cada checkbox
        -- cliqueado que otorgue puntuación», y el catálogo de familias puede
        -- crecer sin tocar la base. Por eso va por prefijo y no enumerado:
        -- `enfoque_c52_discapacidad`, `enfoque_c52_etnico_narp`, …
        -- El largo de la columna (40) acota el nombre.
        OR tipo LIKE 'enfoque\_%'
    );

COMMIT;
