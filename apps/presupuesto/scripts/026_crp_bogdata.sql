-- ═══════════════════════════════════════════════════════════════════════
-- DDL 026 — La ingesta del CRP de BogData/SAP
--
-- ESCRITO Y MEDIDO CONTRA EL ARCHIVO REAL, NO APLICADO.
-- Fuente: «CRP 07092026.xlsx», centro gestor 0008-01, vigencia 2026,
-- corte 2026-09-07. 2.630 filas × 52 columnas, hoja «Data».
--
-- POR QUÉ HACE FALTA. innovaK tiene 25 contratos cargados; este reporte trae
-- **2.265 compromisos y 1.412 terceros por $226.745 M**. Estábamos viendo el
-- 1 % de la contratación de la localidad. Y trae cuatro cosas que SECOP no
-- publica: la cadena CDP→CRP, las anulaciones ($37.489 M) y reintegros, las
-- obligaciones por pagar ($133.786 M — el 61 % del archivo) y el tipo de
-- documento del tercero, que es lo que separa persona natural de jurídica
-- (1.244 naturales con el 19,7 % contra 162 jurídicas con el 64,9 %).
--
-- SE REUSA LO QUE HAY, NO SE DUPLICA. La tabla `crp` YA EXISTE con 48
-- columnas y CERO filas, igual que `rubro`, `tipo_compromiso`,
-- `modalidad_seleccion` y `fondo`. Crear tablas paralelas repondría el
-- problema de los modelos duplicados que este repo ya pagó una vez. Se
-- corrigen con ALTER, que sobre tablas vacías no puede perder nada.
--
-- LOS TIPOS DE `crp` NO AGUANTAN EL DATO, y no es opinable — medido contra el
-- archivo:
--
--   valor_crp / valor_neto / autorizacion_giro   integer   máx $25.884.380.186
--   n_interno_crp                                integer   máx  5.001.102.873
--        → el tope de `integer` es 2.147.483.647. DESBORDA.
--   anulaciones / reintegros                     varchar   son plata
--   objeto                                       varchar(256)  llega a 1.404
--   no_compromiso                                integer   es '002-2026', texto
--   rubro_codigo                                 integer   es 'O2301174599…'
--   numero_doc_bp_beneficiario                   integer   NIT lleva ceros
--
-- Rollback en 026_crp_bogdata_rollback.sql.
-- ═══════════════════════════════════════════════════════════════════════

BEGIN;

-- ── 1. La CARGA. Cada corte es una fila acá ────────────────────────────
--
-- Los valores del reporte (#38-43) son SALDOS ACUMULADOS al corte, no
-- movimientos. Sin una entidad de carga no hay dónde anclar «a qué fecha
-- corresponde este saldo», y dos cortes distintos serían indistinguibles.
CREATE TABLE IF NOT EXISTS crp_carga (
    id                  BIGSERIAL PRIMARY KEY,
    archivo_nombre      VARCHAR(255) NOT NULL,
    -- SHA-256 del archivo. Rechaza «este mismo archivo ya se subió», que es
    -- la pregunta que interesa; un Excel reguardado sin cambios de dato
    -- cambia de bytes y TIENE que poder subirse.
    hash_sha256         VARCHAR(64) UNIQUE,
    -- «Fecha Final» del reporte (#4): el corte que el propio archivo declara.
    -- NO la fecha de subida: dos personas pueden cargar el mismo corte en
    -- días distintos y sigue siendo ese corte.
    fecha_corte         DATE NOT NULL,
    fecha_inicio_reporte DATE,
    centro_gestor       VARCHAR(10),
    vigencia            INTEGER,
    filas_leidas        INTEGER DEFAULT 0,
    filas_insertadas    INTEGER DEFAULT 0,
    filas_actualizadas  INTEGER DEFAULT 0,
    filas_no_vigentes   INTEGER DEFAULT 0,
    -- Los totales de control del propio archivo, guardados. Permiten
    -- contrastar una carga vieja contra su Excel sin volver a abrirlo.
    total_valor_crp     NUMERIC(20,2),
    total_anulaciones   NUMERIC(20,2),
    total_reintegros    NUMERIC(20,2),
    total_valor_neto    NUMERIC(20,2),
    total_aut_giro      NUMERIC(20,2),
    total_sin_aut_giro  NUMERIC(20,2),
    -- Lo que no cruzó, para que la carga no lo esconda.
    compromisos_sin_contrato INTEGER DEFAULT 0,
    rubros_sin_proyecto      INTEGER DEFAULT 0,
    nota                TEXT,
    cargado_por_id      INTEGER REFERENCES usuario(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_crp_carga_corte ON crp_carga (fecha_corte DESC);

COMMENT ON TABLE crp_carga IS
 'Una subida del reporte de CRP de BogData. Los valores del CRP son saldos '
 'acumulados al corte: sin esta tabla no hay a qué fecha atribuirlos.';

-- ── 2. El TERCERO de SAP ───────────────────────────────────────────────
--
-- La llave es el DOCUMENTO, no el nombre: el archivo trae 1.414 nombres
-- distintos para 1.409 documentos, o sea que el mismo tercero aparece
-- escrito de varias formas. Y `bp_sap` es el id interno de SAP, que puede
-- cambiar entre cargas.
--
-- SON DATOS PERSONALES (cédulas y nombres de contratistas): ningún endpoint
-- público puede exponer `num_doc`, y el RBAC es el mismo del módulo de
-- contratos.
CREATE TABLE IF NOT EXISTS tercero_sap (
    id          BIGSERIAL PRIMARY KEY,
    tipo_doc    VARCHAR(10) NOT NULL,
    num_doc     VARCHAR(30) NOT NULL,
    nombre      VARCHAR(200),
    bp_sap      BIGINT,
    -- Se deriva de `tipo_doc` al cargar y se guarda: la pregunta «cuánto se
    -- contrató con personas naturales» no puede depender de que cada consulta
    -- recuerde qué tipos son cuáles.
    es_juridica BOOLEAN,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_tercero_sap_doc UNIQUE (tipo_doc, num_doc)
);
CREATE INDEX IF NOT EXISTS idx_tercero_sap_bp ON tercero_sap (bp_sap);
CREATE INDEX IF NOT EXISTS idx_tercero_sap_juridica ON tercero_sap (es_juridica);

COMMENT ON TABLE tercero_sap IS
 'Beneficiarios del CRP (BogData). Llave por documento, no por nombre: el '
 'archivo trae 1.414 nombres para 1.409 documentos. Contiene datos '
 'personales — no exponer num_doc en endpoints públicos.';

-- ── 3. `crp`: los tipos que no aguantan ────────────────────────────────
-- La tabla está en CERO filas: el USING no puede perder datos.
--
-- EL ORDEN IMPORTA. `crp.rubro_codigo` tiene FK a `rubro.codigo`, y Postgres
-- rechaza dejar los dos lados con tipos distintos aunque sea por un instante:
--
--   ERROR: foreign key constraint "crp_rubro_codigo_fkey" cannot be
--   implemented — Key columns "rubro_codigo" and "codigo" are of
--   incompatible types: character varying and integer.
--
-- Se suelta la FK, se cambian los dos lados y se vuelve a poner. Las otras 13
-- FKs de `crp` apuntan a columnas que NO cambian de tipo, así que no se tocan.
ALTER TABLE crp DROP CONSTRAINT IF EXISTS crp_rubro_codigo_fkey;
ALTER TABLE rubro ALTER COLUMN codigo TYPE VARCHAR(30) USING codigo::text;

ALTER TABLE crp
    ALTER COLUMN valor_crp         TYPE NUMERIC(20,2),
    ALTER COLUMN valor_neto        TYPE BIGINT USING valor_neto::bigint,
    ALTER COLUMN autorizacion_giro TYPE BIGINT USING autorizacion_giro::bigint,
    ALTER COLUMN com_sin_aut_giro  TYPE BIGINT USING com_sin_aut_giro::bigint,
    ALTER COLUMN anulaciones       TYPE BIGINT USING NULLIF(anulaciones, '')::bigint,
    ALTER COLUMN reintegros        TYPE BIGINT USING NULLIF(reintegros, '')::bigint,
    ALTER COLUMN n_interno_crp     TYPE BIGINT USING n_interno_crp::bigint,
    ALTER COLUMN n_interno_cdp     TYPE BIGINT USING n_interno_cdp::bigint,
    ALTER COLUMN objeto            TYPE TEXT,
    ALTER COLUMN descripcion       TYPE TEXT,
    ALTER COLUMN no_compromiso     TYPE VARCHAR(30) USING no_compromiso::text,
    ALTER COLUMN rubro_codigo      TYPE VARCHAR(30) USING rubro_codigo::text,
    ALTER COLUMN concepto_gasto_codigo TYPE VARCHAR(30) USING concepto_gasto_codigo::text,
    ALTER COLUMN numero_doc_bp_beneficiario TYPE VARCHAR(30) USING numero_doc_bp_beneficiario::text,
    ALTER COLUMN bp_beneficiario   TYPE BIGINT USING bp_beneficiario::bigint,
    ALTER COLUMN ejercicio         TYPE INTEGER USING EXTRACT(YEAR FROM ejercicio)::integer;

-- ── 4. `crp`: lo que falta ─────────────────────────────────────────────
ALTER TABLE crp
    ADD COLUMN IF NOT EXISTS carga_id BIGINT REFERENCES crp_carga(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS tercero_id BIGINT REFERENCES tercero_sap(id) ON DELETE SET NULL,
    -- El compromiso normalizado. El raw se conserva en `no_compromiso`
    -- porque hay 10 formatos que no parsean (EDIL, EPS017, 'RES 541',
    -- '934 2025'…) y perder el original haría imposible revisarlos.
    ADD COLUMN IF NOT EXISTS compromiso_numero INTEGER,
    ADD COLUMN IF NOT EXISTS compromiso_anio   INTEGER,
    ADD COLUMN IF NOT EXISTS tipo_compromiso_desc VARCHAR(80),
    ADD COLUMN IF NOT EXISTS rubro_desc        VARCHAR(150),
    ADD COLUMN IF NOT EXISTS fondo_desc        VARCHAR(60),
    ADD COLUMN IF NOT EXISTS modalidad_desc    VARCHAR(80),
    ADD COLUMN IF NOT EXISTS texto_id_proyecto VARCHAR(60),
    ADD COLUMN IF NOT EXISTS programa_financiamiento VARCHAR(30),
    ADD COLUMN IF NOT EXISTS fecha_inicio_compromiso DATE,
    ADD COLUMN IF NOT EXISTS fecha_fin_compromiso    DATE,
    -- El rubro y el PEP NO identifican proyecto en las obligaciones por
    -- pagar (1.602 filas, 61 %): se resuelven después cruzando el contrato
    -- contra el CRP de la vigencia original. La bandera evita que alguien
    -- lea el `proyecto_id` nulo como un error de carga.
    ADD COLUMN IF NOT EXISTS es_obligacion_por_pagar BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS es_funcionamiento       BOOLEAN NOT NULL DEFAULT FALSE,
    -- Lo que desaparece de un corte nuevo se marca, no se borra: perder la
    -- fila perdería la respuesta a «¿desde cuándo dejó de estar?».
    ADD COLUMN IF NOT EXISTS vigente BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- La PK natural. Verificado contra el archivo: 2.630 filas, 2.630 pares
-- únicos, cero duplicados. Es lo que permite el upsert idempotente.
CREATE UNIQUE INDEX IF NOT EXISTS uq_crp_interno_posicion
    ON crp (n_interno_crp, n_posicion_crp);

CREATE INDEX IF NOT EXISTS idx_crp_carga     ON crp (carga_id);
CREATE INDEX IF NOT EXISTS idx_crp_contrato  ON crp (contrato_id);
CREATE INDEX IF NOT EXISTS idx_crp_proyecto  ON crp (proyecto_id);
CREATE INDEX IF NOT EXISTS idx_crp_tercero   ON crp (tercero_id);
CREATE INDEX IF NOT EXISTS idx_crp_rubro     ON crp (rubro_codigo);
CREATE INDEX IF NOT EXISTS idx_crp_compromiso ON crp (compromiso_numero, compromiso_anio);
CREATE INDEX IF NOT EXISTS idx_crp_vigente   ON crp (vigente) WHERE vigente;

-- ── 4b. `crp.id` no tenía secuencia ────────────────────────────────────
--
-- Es la deuda S5 que este repo documenta: cinco tablas con `id` NOT NULL sin
-- DEFAULT, que obligan al patrón `MAX(id)+1` a mano. El propio CLAUDE.md dice
-- que la solución canónica es la secuencia en la BD y que un INSERT nuevo NO
-- debe copiar el patrón viejo — y sin esto la tabla es directamente
-- inutilizable: el primer INSERT muere con «null value in column id».
--
-- `IDENTITY` y no `serial` porque la columna ya existe. Arranca en 1: la
-- tabla está vacía.
DO $$
BEGIN
    IF (SELECT column_default FROM information_schema.columns
        WHERE table_name = 'crp' AND column_name = 'id') IS NULL THEN
        EXECUTE 'CREATE SEQUENCE IF NOT EXISTS crp_id_seq OWNED BY crp.id';
        EXECUTE 'SELECT setval(''crp_id_seq'', COALESCE((SELECT MAX(id) FROM crp), 0) + 1, false)';
        EXECUTE 'ALTER TABLE crp ALTER COLUMN id SET DEFAULT nextval(''crp_id_seq'')';
    END IF;
END $$;

-- ── 5. `rubro`: hoy son dos columnas y hace falta clasificar ───────────
-- 49 valores en el archivo. El tipo decide si el rubro identifica proyecto:
-- los de inversión 2026 lo llevan en las posiciones 17-20; los de
-- obligaciones por pagar y funcionamiento, no.
-- El tipo de `rubro.codigo` ya se cambió arriba, junto con la FK.
ALTER TABLE rubro
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(24),
    ADD COLUMN IF NOT EXISTS proyecto_cod VARCHAR(10);

-- Y la FK vuelve, ahora con los dos lados en VARCHAR.
ALTER TABLE crp
    ADD CONSTRAINT crp_rubro_codigo_fkey
    FOREIGN KEY (rubro_codigo) REFERENCES rubro(codigo) ON DELETE SET NULL;

COMMENT ON COLUMN rubro.tipo IS
 'inversion | funcionamiento | obligacion_por_pagar. Decide si el código '
 'del rubro identifica un proyecto del PDL.';

COMMIT;
