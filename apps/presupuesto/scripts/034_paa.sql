-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║ 034 · El espejo del Plan Anual de Adquisiciones (PAA) de Kennedy          ║
-- ╚══════════════════════════════════════════════════════════════════════════╝
--
-- ✅ APLICADO el 2026-10-13. Backup del día: 12 h de antigüedad al aplicar.
--
--    Se aplicó dos veces: la primera versión dejaba `proceso_estado` en dos
--    valores, y la primera corrida en seco mostró que faltaba un tercero —hay
--    3 filas cuyo proceso el plan NOMBRA pero con un texto que no se puede
--    parsear, y meterlas en «no_definido» las habría contado como ítems
--    planeados sin contratar—. Se corrió el rollback con la tabla todavía en
--    cero filas y se volvió a aplicar corregido, antes de commitear. La
--    tercera pasada fue por los tipos (ver abajo), también antes de commitear y
--    con el espejo todavía sin servir a nadie.
--
-- ## Tres tablas, y por qué no una
--
-- El origen son dos datasets de datos.gov.co y vienen DESNORMALIZADOS:
--
--     b6m4-qgqv  «PAA - Encabezado»  → 1 fila por (entidad, año): presupuesto,
--                                       versión, estado, contactos
--     9sue-ezhx  «PAA»               → 1 fila por (ítem × proceso relacionado)
--
-- Medido el 2026-10-13 sobre Kennedy (codigo_entidad 702292459):
--
--     filas del PAA ....................... 6.579   (2017-2026)
--     identificadores de ítem distintos ... 6.333
--     ítems con MÁS de una fila ...........   216   (246 filas de más)
--
-- Y lo que cambia dentro de un grupo de esas filas es EXACTAMENTE esto:
--
--     procesos_relacionados ... en 216 grupos
--     url_proceso ............. en 155 grupos
--     cualquier otro campo .... en NINGUNO
--
-- O sea: un mismo ítem planeado puede ir a varios procesos. Con una sola tabla
-- y `id` como llave se pierden 246 filas en silencio —y con ellas los procesos
-- que esos ítems alimentaron—, que es justo el cruce que el PAA sirve para hacer.
--
-- ## La llave natural de la tabla de procesos, medida y no supuesta
--
--     (item_id, proceso_ref_origen) ... 6.579 llaves · 0 repetidas · 0 filas perdidas
--     (item_id, url_proceso) .......... 6.506 llaves · 64 repetidas · 73 filas PERDIDAS
--
-- Se escribe porque con `secop_suspension` la llave «obvia» —(contrato, tipo,
-- fecha de aprobación)— resultó no ser única y había que medirla.
--
-- ## No hay historial de versiones, y es de la fuente
--
-- El PAA 2025 de Kennedy va en la versión 31, pero los dos datasets solo
-- publican la ÚLTIMA: 1 sola versión distinta por año en los dos. Lo que
-- cambió entre la 30 y la 31 no está en ninguna parte. Se guarda el número y la
-- fecha de versión para poder decir «esto es la versión 31 del 2025-12-15», no
-- para reconstruir nada.
--
-- Detalle que hay que saber: el encabezado va ADELANTADO respecto a los ítems
-- —2026 dice versión 19 en el encabezado y 16 en los ítems—, así que las dos
-- tablas pueden quedar desfasadas por unas versiones. No es un error de la
-- ingesta.
--
-- Rollback: rollback_034_paa.sql

-- ## varchar(n) solo donde el dominio está acotado
--
-- La primera corrida con escritura se cayó con «value too long for type
-- character varying(200)»: `categorias_unspsc` llega a 530 caracteres porque es
-- una LISTA de códigos UNSPSC, no un código. Medidos los largos máximos del
-- origen, todo lo que es texto libre o una lista quedó en `text` —que en
-- Postgres rinde igual que varchar— y el varchar(n) se reservó para
-- identificadores y códigos, donde el límite sí dice algo. Dimensionar una
-- columna a ojo es apostar a que el origen no crezca.

BEGIN;

-- ── 1 · El encabezado: una fila por (entidad, año) ───────────────────────────
CREATE TABLE IF NOT EXISTS paa_encabezado (
    id                      bigserial PRIMARY KEY,
    identificador_unico     varchar(60)  NOT NULL,
    id_plan                 varchar(60),
    anio                    integer      NOT NULL,
    codigo_entidad          varchar(30)  NOT NULL,
    nombre_entidad          text,
    -- Texto institucional del propio plan. Se guarda porque es parte del
    -- documento oficial, no porque lo usemos hoy.
    mision_vision           text,
    perspectiva_estrategica text,
    nombre_contacto         text,
    telefono_contacto       text,
    correo_contacto         text,
    valor_presupuesto       numeric(20, 2),
    presupuesto_menor       numeric(20, 2),
    presupuesto_minima      numeric(20, 2),
    fecha_publicacion       timestamptz,
    fecha_creacion          timestamptz,
    fecha_modificacion      timestamptz,
    version                 integer,
    estado                  text,
    departamento            text,
    municipio               text,
    hash_fila               varchar(64),
    fuente                  varchar(40) DEFAULT 'b6m4-qgqv',
    synced_at               timestamptz DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_paa_encabezado
    ON paa_encabezado (identificador_unico);
CREATE INDEX IF NOT EXISTS idx_paa_encabezado_anio
    ON paa_encabezado (codigo_entidad, anio);

COMMENT ON COLUMN paa_encabezado.version IS
    'Número de versión del PAA. La fuente NO publica las versiones anteriores: '
    'solo este número y su fecha. Puede ir adelantado respecto a la versión de '
    'los ítems (medido 2026: 19 aquí, 16 en paa_item).';

-- ── 2 · El ítem planeado: una fila por identificador ─────────────────────────
CREATE TABLE IF NOT EXISTS paa_item (
    id                      bigserial PRIMARY KEY,
    item_id                 varchar(80)  NOT NULL,
    identificador_unico     varchar(60),
    anio                    integer      NOT NULL,
    descripcion             text,
    -- El código interno del área, parseado de la descripción. La CONVENCIÓN
    -- cambia cada año y por eso viaja al lado: K-0528 en 2025-2026, ID_900 en
    -- 2024, PS-345-2178-2767-14919 en 2022 (que trae proyecto y meta adentro).
    -- Cobertura medida 2026-10-13: 2025 100 % · 2024 100 % · 2026 81,5 % ·
    -- 2022 82,1 % · el resto de los años 0 %.
    codigo_interno          varchar(60),
    codigo_interno_tipo     varchar(20),
    fecha_esperada_inicio   text,
    fecha_esperada_recepcion text,
    duracion_esperada       text,
    unidad_duracion         text,
    origen_recursos         text,
    valor_total_esperado    numeric(20, 2),
    valor_presupuesto       numeric(20, 2),
    requiere_vigencias_fut  text,
    estado_solicitud        text,
    modalidad               text,
    categorias_unspsc       text,
    causal_contratacion     text,
    grupo_procedimiento     text,
    tipo                    text,
    version_paa             integer,
    fecha_version           timestamptz,
    fecha_carga_paa         timestamptz,
    hash_fila               varchar(64),
    fuente                  varchar(40) DEFAULT '9sue-ezhx',
    synced_at               timestamptz DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_paa_item ON paa_item (item_id);
CREATE INDEX IF NOT EXISTS idx_paa_item_anio ON paa_item (anio);
CREATE INDEX IF NOT EXISTS idx_paa_item_codigo
    ON paa_item (codigo_interno) WHERE codigo_interno IS NOT NULL;

-- ── 3 · El proceso al que fue ese ítem ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS paa_item_proceso (
    id                  bigserial PRIMARY KEY,
    item_id             varchar(80) NOT NULL,
    -- El valor CRUDO, incluido el literal «No Definido» que trae el 71,0 % de
    -- las filas. Es la llave natural y además la única forma de distinguir
    -- «el plan dice que todavía no hay proceso» de «no tenemos el dato».
    proceso_ref_origen  text        NOT NULL,
    -- TRES estados, no dos. «el plan dice que todavía no hay proceso» y «el
    -- plan nombra algo que no pudimos leer» son hechos distintos, y mezclarlos
    -- infla el conteo de ítems planeados sin contratar. Medido en 2026: 438
    -- no_definido contra 3 ilegibles —«FDLK-CD137-2026», al que le falta un
    -- guión, y «CPS-088-2026», que es un número de CONTRATO metido en el campo
    -- del proceso—.
    proceso_estado      varchar(20) NOT NULL,
    -- Parseados. `null` cuando no se puede, nunca forzados.
    proceso_ref         varchar(80),
    proceso_sipse       varchar(20),
    proceso_notice_id   varchar(60),
    url_proceso         text,
    hash_fila           varchar(64),
    fuente              varchar(40) DEFAULT '9sue-ezhx',
    synced_at           timestamptz DEFAULT now(),
    CONSTRAINT ck_paa_proceso_estado
        CHECK (proceso_estado IN ('declarado', 'no_definido', 'ilegible')),
    -- Un proceso declarado tiene que traer su referencia parseada; si no, es
    -- `ilegible` y se ve. Al revés también: `ilegible` sin texto crudo que
    -- mostrar no tiene sentido, porque lo único que aporta es ese texto.
    CONSTRAINT ck_paa_proceso_declarado
        CHECK (proceso_estado <> 'declarado' OR proceso_ref IS NOT NULL),
    CONSTRAINT ck_paa_proceso_ilegible
        CHECK (proceso_estado <> 'ilegible'
               OR (proceso_ref IS NULL AND length(trim(proceso_ref_origen)) > 0))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_paa_item_proceso
    ON paa_item_proceso (item_id, proceso_ref_origen);
-- El cruce con el espejo de contratos es por acá (ver DDL 033).
CREATE INDEX IF NOT EXISTS idx_paa_proceso_notice
    ON paa_item_proceso (proceso_notice_id) WHERE proceso_notice_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_paa_proceso_sipse
    ON paa_item_proceso (proceso_sipse) WHERE proceso_sipse IS NOT NULL;

COMMENT ON COLUMN paa_item_proceso.proceso_sipse IS
    'Código de SIPSE, sacado del paréntesis de procesos_relacionados. Validado '
    'contra el espejo de contratos el 2026-10-13: 790 de los 816 códigos del '
    'PAA (96,8 %) aparecen en la referencia de un contrato nuestro.';

COMMIT;
