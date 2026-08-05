-- =====================================================================
-- Módulo Educación — DDL-1
--   colegio_sede            : las sedes de los colegios distritales de Kennedy
--   entrega_insumo_colegio  : qué se le entregó a cada sede, con qué contrato
--
-- POR QUÉ una tabla propia y no `escuela`:
--   `escuela` son las escuelas de formación de Cultura y Deporte (241 filas,
--   las dicta la Alcaldía). Un colegio distrital es de la Secretaría de
--   Educación, tiene DANE, matrícula y sedes jerárquicas. Meterlos en la misma
--   tabla obligaría a que la mitad de las columnas fueran NULL en cada caso.
--
-- FUENTE (verificada 2026-08-05, sin API key):
--   Sedes    → serviciosgis.catastrobogota.gov.co/arcgis/rest/services/
--              educacion/infraestructuraeducativa/MapServer/0  (corte 2025-12-31)
--   Matrícula→ .../educacion/matricula/MapServer/1  campo TMATRIC_GENERAL
--              (corte 2025-04-30), cruza por DANE12_SED
--   Kennedy (COD_LOCA='08', SECTOR=2 Oficial): 48 colegios / 79 sedes
--     · 44 colegios / 75 sedes Distritales
--     ·  4 colegios /  4 sedes Distrital - Administración Contratada
--   Licencia CC BY 4.0 — atribuir "Secretaría de Educación del Distrito /
--   Catastro Bogotá - IDECA".
--
-- APLICAR tras backup < 24 h (~/Proyectos/postgres/backup_postgres.sh).
-- El contenedor innova_k NO tiene psql: aplicar con
--   connection.cursor().execute(open('.../001_educacion_setup.sql').read())
-- REVERSA al final del archivo.
-- =====================================================================
BEGIN;

-- ── Sedes de colegios ────────────────────────────────────────────────
-- La unidad es la SEDE, no el colegio: los insumos se entregan en una sede
-- concreta y la matrícula se cuenta por sede. El colegio queda como los dos
-- campos `*_establecimiento`, que se repiten entre las sedes hermanas.
CREATE TABLE IF NOT EXISTS colegio_sede (
    id BIGSERIAL PRIMARY KEY,

    -- Identidad oficial. El DANE de sede es único en todo el país y es la
    -- llave con la que se concilia contra cualquier archivo que mande SED.
    dane_sede              VARCHAR(12) NOT NULL UNIQUE,
    dane_establecimiento   VARCHAR(12) NOT NULL,
    nombre_establecimiento TEXT NOT NULL,
    nombre_sede            TEXT NOT NULL,
    orden_sede             VARCHAR(4),   -- A (principal) / B / C / D

    -- Dominios de SED, se guardan como código y se traducen en el modelo.
    sector SMALLINT,   -- 1 No Oficial, 2 Oficial
    clase  SMALLINT,   -- 1 Distrital, 2 Distrital - Adm. Contratada,
                       -- 3 Oficial - Régimen Especial, 4 Privado, ...
    jornada_genero SMALLINT,  -- dominio GENERO de la capa (mixto/femenino/...)
    calendario     SMALLINT,

    direccion        TEXT,
    barrio_declarado TEXT,    -- BARRIO__GE: lo que declara SED, sin resolver
    telefono TEXT,
    email    TEXT,
    web      TEXT,

    localidad_codigo INTEGER,
    -- Ojo: los campos de la capa se llaman NOM_UPZ / NOM_UPL y el alias dice
    -- "Nombre de la UPZ", pero lo que traen es el CÓDIGO ('44', '113'…).
    -- Verificado sobre las 79 sedes: salen los 12 códigos de UPZ de Kennedy.
    upz_codigo INTEGER,
    -- Sin FK a `upl` a propósito: ese catálogo se sembró con las 9 UPL de
    -- Kennedy y esta capa trae la numeración distrital (13…18). Hasta no
    -- confirmar que son la misma numeración, una FK rompería el cargue.
    upl_codigo SMALLINT,

    latitud  NUMERIC(9,6),
    longitud NUMERIC(9,6),
    -- Mismo criterio que `escuela.estrato_ideca`: oficial, point-in-polygon
    -- sobre manzana_estrato. Lo puebla `asignar_estrato_sedes`.
    estrato_ideca SMALLINT,

    -- Matrícula: viene de OTRA capa y con OTRA fecha de corte. Por eso la
    -- fecha va al lado del número — decir "1.200 alumnos" sin decir a qué
    -- fecha es lo que hace que dos informes no cuadren.
    matricula_total INTEGER,
    matricula_corte DATE,

    activo BOOLEAN NOT NULL DEFAULT TRUE,

    fuente      VARCHAR(20) NOT NULL DEFAULT 'IDECA-SED',
    fecha_corte DATE,
    properties  JSONB,          -- el registro crudo, para no perder campos
    synced_at   TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_colegio_sede_est
    ON colegio_sede (dane_establecimiento);
CREATE INDEX IF NOT EXISTS idx_colegio_sede_loc
    ON colegio_sede (localidad_codigo);
CREATE INDEX IF NOT EXISTS idx_colegio_sede_upz
    ON colegio_sede (upz_codigo);
-- Parcial: el mapa solo consulta las que tienen punto.
CREATE INDEX IF NOT EXISTS idx_colegio_sede_geo
    ON colegio_sede (latitud, longitud) WHERE latitud IS NOT NULL;

-- ── Insumos entregados a una sede ────────────────────────────────────
-- El caso real: al liquidar los contratos de 2025, Educación pasa un acta que
-- dice "a tal colegio le entregamos tantos de esto". Esta tabla es donde eso
-- aterriza para que después sí se pueda sumar.
--
-- NO CONFUNDIR con `entrega_insumo` (apps.entregas), que ya existe:
--   entrega_insumo         → a una PERSONA, con cédula y firma, capturada en
--                            un evento tipo ENTREGA. Cabecera + puente porque
--                            un acta cubre a alguien con varios elementos.
--   entrega_insumo_colegio → a una SEDE, reportada por el contratista al
--                            liquidar. Plana (una fila = un insumo en una
--                            sede) porque el dato llega en planilla y así se
--                            carga y se suma sin armar cabeceras falsas; el
--                            acta se reconstruye agrupando por `acta_numero`.
-- Las dos comparten el catálogo `implemento`, que es lo que hace que las
-- cifras sean comparables entre áreas.
CREATE TABLE IF NOT EXISTS entrega_insumo_colegio (
    id BIGSERIAL PRIMARY KEY,

    colegio_sede_id BIGINT NOT NULL
        REFERENCES colegio_sede(id) ON DELETE RESTRICT,
    -- Nullable a propósito: hay entregas que llegan antes de que el contrato
    -- esté cargado. Sin esto el área no puede registrar nada y termina en un
    -- Excel paralelo, que es exactamente lo que estamos evitando.
    contrato_id INTEGER
        REFERENCES contrato(id) ON DELETE SET NULL,

    vigencia SMALLINT NOT NULL,

    -- Catálogo compartido con el Banco de Iniciativas (35 filas). Es lo que
    -- permite preguntar "cuántos balones entregamos en 2025" sin pelear con
    -- la ortografía de cada acta.
    implemento_codigo SMALLINT REFERENCES implemento(codigo),
    -- Lo que dice el acta, tal cual. Se conserva aunque haya catálogo: es el
    -- soporte, y a veces el acta es más específica que el catálogo.
    descripcion TEXT,

    cantidad NUMERIC(14,2) NOT NULL DEFAULT 0,
    unidad   VARCHAR(20),
    valor_unitario NUMERIC(18,4),
    valor_total    NUMERIC(18,4),
    -- Alumnos beneficiados por ESTA entrega. No es la matrícula de la sede:
    -- una dotación de un aula no beneficia a todo el colegio.
    beneficiarios INTEGER,

    fecha_entrega DATE,
    acta_numero VARCHAR(60),
    observacion TEXT,

    registrado_por_id INTEGER REFERENCES usuario(id) ON DELETE SET NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Una fila sin catálogo NI texto no dice qué se entregó: es basura.
    CONSTRAINT ck_entrega_insumo_identificado
        CHECK (implemento_codigo IS NOT NULL OR nullif(btrim(descripcion), '') IS NOT NULL),
    CONSTRAINT ck_entrega_cantidad_positiva CHECK (cantidad >= 0)
);

CREATE INDEX IF NOT EXISTS idx_entrega_insumo_sede
    ON entrega_insumo_colegio (colegio_sede_id);
CREATE INDEX IF NOT EXISTS idx_entrega_insumo_contrato
    ON entrega_insumo_colegio (contrato_id);
CREATE INDEX IF NOT EXISTS idx_entrega_insumo_vigencia
    ON entrega_insumo_colegio (vigencia);

COMMIT;

-- =====================================================================
-- REVERSA (si hay que deshacer):
--   BEGIN;
--   DROP TABLE IF EXISTS entrega_insumo_colegio;
--   DROP TABLE IF EXISTS colegio_sede;
--   COMMIT;
-- =====================================================================
