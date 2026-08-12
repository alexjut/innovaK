-- 004 · Cargue masivo de beneficiarios de educación posmedia (2026-08-12)
--
-- POR QUÉ
-- El área entrega los beneficiarios en un Excel institucional (175 filas para
-- la vigencia 2025, y los de 2026 ya salieron en otro archivo). Hoy la única
-- forma de meterlos es el formulario público del QR, uno por uno y con firma
-- del ciudadano — que no existe para una carga administrativa. `entrega_beca`
-- tampoco tiene dónde guardar la vigencia, los códigos SNIES ni de dónde vino
-- la fila.
--
-- QUÉ HACE
--   1. Le agrega a `entrega_beca` las cinco columnas que faltan.
--   2. Cambia la llave de unicidad: de (evento, documento) a la MATRÍCULA.
--   3. Crea `cargue_beneficiarios`, la cabecera del lote (archivo, hash, quién
--      y en qué estado), para que procesar sea trazable y reversible.
--   4. Ata el tipo de evento de becas a la actividad del plan.
--
-- LA DECISIÓN QUE MÁS PESA: LA LLAVE DE UNICIDAD
-- Hoy hay `UNIQUE (evento_id, numero_documento)`, o sea «una persona, una fila
-- por evento». Eso ES el caso normal del QR, pero rechaza dos hechos ciertos
-- del archivo del área:
--
--   · una persona con DOS matrículas en la misma vigencia (verificado: el
--     documento 1000494673 aparece con dos programas en dos instituciones);
--   · la misma persona reapareciendo el año siguiente, que es exactamente lo
--     que significa el componente de PERMANENCIA.
--
-- La llave nueva es (vigencia, documento, snies_ies, snies_programa) con
-- NULLS NOT DISTINCT (PostgreSQL 16.14, verificado). Con eso:
--
--   misma persona, misma vigencia, mismo programa  →  RECHAZA (doble digitación)
--   misma persona, misma vigencia, otro programa   →  acepta (dos matrículas)
--   misma persona, otra vigencia                   →  acepta (permanencia)
--   flujo QR (sin códigos SNIES)                   →  RECHAZA la segunda del año
--
-- El último renglón es el que hace falta explicar: `NULLS NOT DISTINCT` trata
-- dos NULL como iguales, así que para las filas del QR —que no traen SNIES— la
-- llave colapsa a (vigencia, documento) y la protección queda MÁS fuerte que
-- la de hoy: antes era por evento, y si Educación abría dos eventos de captura
-- en el mismo año la misma persona podía inscribirse en los dos.
--
-- SIN DATOS QUE MIGRAR
-- `entrega_beca` tiene 0 filas (verificado 2026-08-12), así que ninguna fila
-- existente puede violar la llave nueva ni el CHECK de vigencia.
--
-- APLICAR (requiere OK explícito de Alex + backup < 24 h):
--   docker exec innova_k python -c "
--   import django,os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
--   django.setup()
--   from django.db import connection
--   connection.cursor().execute(open('apps/jovenes_a_la_e/scripts/004_cargue_beneficiarios.sql').read())"
--
-- (el contenedor NO trae `psql`, y desde el host la conexión la rechaza
--  `pg_hba.conf`: se aplica por cursor, como el resto)
--
-- DESPUÉS: correr `004_cargue_beneficiarios_verificacion.sql`.

BEGIN;

-- ════════════════════════════════════════════════════════════════════════
-- 1 · Columnas nuevas en `entrega_beca`
-- ════════════════════════════════════════════════════════════════════════

ALTER TABLE entrega_beca
    ADD COLUMN IF NOT EXISTS vigencia       SMALLINT,
    ADD COLUMN IF NOT EXISTS origen         VARCHAR(20)  NOT NULL DEFAULT 'QR',
    ADD COLUMN IF NOT EXISTS snies_programa VARCHAR(20),
    ADD COLUMN IF NOT EXISTS snies_ies      VARCHAR(20),
    ADD COLUMN IF NOT EXISTS cargue_id      BIGINT;

-- La vigencia es obligatoria: sin ella se mezclan años en el mismo conteo y la
-- meta es de cuatrienio. El DEFAULT no es decorativo — el formulario público
-- del QR todavía no la manda, y sin default sus inserts empezarían a fallar en
-- el momento en que esto se aplique. El código la pone explícita; el default
-- es la red para lo que aún no la pone.
ALTER TABLE entrega_beca
    ALTER COLUMN vigencia SET DEFAULT date_part('year', now())::smallint;

UPDATE entrega_beca SET vigencia = date_part('year', created_at)::smallint
 WHERE vigencia IS NULL;   -- 0 filas hoy; queda por si se aplica más tarde

ALTER TABLE entrega_beca
    ALTER COLUMN vigencia SET NOT NULL;

-- Sin techo a propósito: un rango cerrado (2024–2032) es deuda con fecha de
-- vencimiento conocida, y reventaría un 1 de enero en producción.
ALTER TABLE entrega_beca
    DROP CONSTRAINT IF EXISTS ck_entrega_beca_vigencia;
ALTER TABLE entrega_beca
    ADD CONSTRAINT ck_entrega_beca_vigencia CHECK (vigencia >= 2024);

-- MAYÚSCULA por consistencia con la columna que significa lo mismo:
-- `presu_avance_ind_periodo.origen` (EVENTO/MANUAL/AJUSTE). En este proyecto
-- los ESTADOS van en minúscula y los TIPOS/ORÍGENES en mayúscula.
ALTER TABLE entrega_beca
    DROP CONSTRAINT IF EXISTS ck_entrega_beca_origen;
ALTER TABLE entrega_beca
    ADD CONSTRAINT ck_entrega_beca_origen CHECK (origen IN ('QR', 'CARGA'));

COMMENT ON COLUMN entrega_beca.vigencia IS
    'Año del beneficio. La meta es de cuatrienio: sin esto se mezclan años.';
COMMENT ON COLUMN entrega_beca.origen IS
    'QR = la capturó el ciudadano (lleva firma). CARGA = vino de un lote administrativo.';
COMMENT ON COLUMN entrega_beca.snies_programa IS
    'Código SNIES/SIET del programa. VARCHAR y no entero: conserva ceros a la izquierda.';
COMMENT ON COLUMN entrega_beca.snies_ies IS
    'Código SNIES/SIET de la institución. Mismo tipo y formato que tendrá '
    '`institucion_educativa.codigo_snies` (catálogo con lat/lon que se crea en '
    'la rama del mapa), para que el join sea directo y sin CAST.';

-- ════════════════════════════════════════════════════════════════════════
-- 2 · La llave de unicidad pasa de la persona a la MATRÍCULA
-- ════════════════════════════════════════════════════════════════════════

DROP INDEX IF EXISTS uq_entrega_beca_evento_doc;

CREATE UNIQUE INDEX IF NOT EXISTS uq_entrega_beca_matricula
    ON entrega_beca (vigencia, numero_documento, snies_ies, snies_programa)
    NULLS NOT DISTINCT;

CREATE INDEX IF NOT EXISTS idx_entrega_beca_vigencia ON entrega_beca (vigencia);
CREATE INDEX IF NOT EXISTS idx_entrega_beca_cargue   ON entrega_beca (cargue_id);

-- ════════════════════════════════════════════════════════════════════════
-- 3 · La cabecera del lote
-- ════════════════════════════════════════════════════════════════════════
--
-- Una fila por archivo procesado. Existe para tres cosas concretas: que el
-- mismo archivo no se procese dos veces, que se pueda deshacer un cargue
-- entero, y que el detalle de una entrega pueda decir de dónde salió — que no
-- la confundan con un acta firmada por el ciudadano.

CREATE TABLE IF NOT EXISTS cargue_beneficiarios (
    id             BIGSERIAL   PRIMARY KEY,
    -- INTEGER, no BIGINT: `evento.id` y `usuario.id` son integer en esta base
    -- (el modelo Django dice BigAutoField, pero manda la columna real).
    evento_id      INTEGER     NOT NULL REFERENCES evento(id)   ON DELETE RESTRICT,
    usuario_id     INTEGER              REFERENCES usuario(id)  ON DELETE SET NULL,
    vigencia       SMALLINT    NOT NULL,
    archivo_nombre TEXT        NOT NULL,
    archivo_sha256 CHAR(64)    NOT NULL,
    estado         VARCHAR(20) NOT NULL DEFAULT 'validado',
    filas_total    INTEGER     NOT NULL DEFAULT 0,
    filas_ok       INTEGER     NOT NULL DEFAULT 0,
    filas_error    INTEGER     NOT NULL DEFAULT 0,
    -- Reporte fila a fila tal como lo devuelve el lector, con el número de
    -- fila REAL del Excel: [{fila: 3, estado: 'ok'|'aviso'|'error', ...}]
    reporte        JSONB,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_cargue_estado   CHECK (estado IN ('validado', 'procesado', 'anulado')),
    CONSTRAINT ck_cargue_vigencia CHECK (vigencia >= 2024)
);

-- Idempotencia: el mismo archivo no se procesa dos veces en la misma vigencia.
-- Parcial a propósito — un lote anulado libera el hash para volver a intentar.
CREATE UNIQUE INDEX IF NOT EXISTS uq_cargue_hash_vigencia
    ON cargue_beneficiarios (vigencia, archivo_sha256)
 WHERE estado <> 'anulado';

CREATE INDEX IF NOT EXISTS idx_cargue_evento ON cargue_beneficiarios (evento_id);

ALTER TABLE entrega_beca
    DROP CONSTRAINT IF EXISTS fk_entrega_beca_cargue;
ALTER TABLE entrega_beca
    ADD CONSTRAINT fk_entrega_beca_cargue
    FOREIGN KEY (cargue_id) REFERENCES cargue_beneficiarios(id) ON DELETE SET NULL;

COMMENT ON TABLE cargue_beneficiarios IS
    'Lote de cargue masivo de beneficiarios. Una fila por archivo procesado.';

-- ════════════════════════════════════════════════════════════════════════
-- 4 · El evento de becas debe colgar del plan
-- ════════════════════════════════════════════════════════════════════════
--
-- Regla de la cadena presupuestal: los beneficiarios cuelgan de un evento, y
-- ese evento tiene que estar atado a una `actividad_plan` para que el avance
-- llegue a un KPI. `JOVENES_BECA` está hoy en FALSE, así que se puede crear un
-- evento de becas suelto y sus beneficiarios no le suman a ninguna meta.

UPDATE tipo_evento
   SET requiere_actividad_plan = TRUE
 WHERE codigo = 'JOVENES_BECA'
   AND requiere_actividad_plan IS DISTINCT FROM TRUE;

COMMIT;
