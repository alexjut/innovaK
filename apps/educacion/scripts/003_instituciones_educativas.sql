-- 003 · Catálogo de instituciones y programas de educación posmedia (2026-08-12)
--
-- POR QUÉ
-- El cargue de beneficiarios guarda los códigos SNIES/SIET en cada fila de
-- `entrega_beca`, pero un código no tiene dónde llevar el nombre oficial, la
-- ciudad ni las coordenadas. Sin eso no hay mapa: hoy sabemos que 18
-- beneficiarios estudian en la institución 2725 y que se llama POLITECNICO
-- GRANCOLOMBIANO, pero no dónde queda.
--
-- Medido sobre lo cargado (2026-08-12): 34 instituciones distintas y 69
-- programas (contando el par institución+programa) para 174 matrículas.
--
-- DOS TABLAS, Y EL NIVEL VA EN EL PROGRAMA
-- Una institución puede ofrecer varios niveles a la vez —el Politécnico dicta
-- tecnologías y carreras profesionales—, así que el nivel es del PROGRAMA. La
-- institución muestra los niveles que ofrece, que se deducen de sus programas.
--
-- LA LLAVE DEL PROGRAMA ES (institución, código)
-- Un mismo código de programa existe en instituciones distintas; hacerlo único
-- global mezclaría dos carreras que no tienen nada que ver.
--
-- MISMO TIPO Y NORMALIZACIÓN QUE `entrega_beca.snies_ies`
-- `VARCHAR(20)`, dígitos, sin ceros a la izquierda perdidos (por eso texto y no
-- entero) y pasados por el mismo normalizador del cargue
-- (`cargue_excel.digitos`). Así el join es directo, sin CAST ni LPAD.
--
-- SNIES vs SIET: son dos registros distintos del Ministerio. Las universidades
-- están en el SNIES; los institutos de educación para el trabajo (ETDH), en el
-- SIET. El archivo del área los mezcla en la misma columna, así que la
-- distinción se guarda acá.
--
-- APLICAR (requiere OK explícito de Alex + backup < 24 h):
--   docker exec innova_k python -c "
--   import django,os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
--   django.setup()
--   from django.db import connection
--   connection.cursor().execute(open('apps/educacion/scripts/003_instituciones_educativas.sql').read())"

BEGIN;

CREATE TABLE IF NOT EXISTS institucion_educativa (
    id            BIGSERIAL   PRIMARY KEY,
    -- Llave natural. Única: es el identificador oficial del Ministerio.
    codigo_snies  VARCHAR(20) NOT NULL UNIQUE,
    nombre        TEXT        NOT NULL,
    -- SNIES = educación superior · SIET = educación para el trabajo (ETDH).
    tipo_registro VARCHAR(10) NOT NULL DEFAULT 'SNIES',
    ciudad        TEXT,
    -- Sin coordenadas al nacer: la institución entra por uso, desde el cargue,
    -- y ubicarla es trabajo del área. Nulo significa «sin ubicar», que la
    -- pantalla muestra como pendiente en vez de esconderlo.
    latitud       NUMERIC(9,6),
    longitud      NUMERIC(9,6),
    -- Cómo entró: CARGUE (la creó un lote) o MANUAL (la creó una persona).
    -- Mayúscula, como `entrega_beca.origen` y `presu_avance_ind_periodo.origen`.
    origen        VARCHAR(20) NOT NULL DEFAULT 'CARGUE',
    observacion   TEXT,
    activa        BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_ie_tipo_registro CHECK (tipo_registro IN ('SNIES', 'SIET')),
    CONSTRAINT ck_ie_origen        CHECK (origen IN ('CARGUE', 'MANUAL')),
    -- O las dos coordenadas o ninguna: media coordenada no ubica nada y
    -- rompería el mapa en silencio.
    CONSTRAINT ck_ie_coordenadas   CHECK (
        (latitud IS NULL AND longitud IS NULL) OR
        (latitud IS NOT NULL AND longitud IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_ie_sin_ubicar ON institucion_educativa (activa)
 WHERE latitud IS NULL;

COMMENT ON TABLE institucion_educativa IS
    'Instituciones donde estudian los beneficiarios de educación posmedia. Se '
    'pueblan por uso desde el cargue y las ubica el área.';
COMMENT ON COLUMN institucion_educativa.codigo_snies IS
    'Código oficial. Mismo tipo y normalización que entrega_beca.snies_ies '
    'para que el join sea directo, sin CAST ni LPAD.';

CREATE TABLE IF NOT EXISTS programa_academico (
    id              BIGSERIAL   PRIMARY KEY,
    institucion_id  BIGINT      NOT NULL REFERENCES institucion_educativa(id) ON DELETE CASCADE,
    codigo_snies    VARCHAR(20) NOT NULL,
    nombre          TEXT        NOT NULL,
    -- Espeja los `choices` de `entrega_beca.nivel_formacion`.
    nivel_formacion VARCHAR(40),
    activo          BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_pa_nivel CHECK (
        nivel_formacion IS NULL OR nivel_formacion IN
        ('etdh', 'tecnico_profesional', 'tecnologo', 'profesional')
    ),
    -- La llave es el PAR: un mismo código existe en instituciones distintas.
    CONSTRAINT uq_programa_institucion_codigo UNIQUE (institucion_id, codigo_snies)
);

CREATE INDEX IF NOT EXISTS idx_pa_institucion ON programa_academico (institucion_id);
CREATE INDEX IF NOT EXISTS idx_pa_nivel       ON programa_academico (nivel_formacion);

COMMENT ON TABLE programa_academico IS
    'Programas por institución. El nivel de formación vive acá y no en la '
    'institución: una IES ofrece varios niveles a la vez.';

COMMIT;
