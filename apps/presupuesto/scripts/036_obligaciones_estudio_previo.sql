-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║ 036 · Las obligaciones específicas, extraídas del estudio previo          ║
-- ╚══════════════════════════════════════════════════════════════════════════╝
--
-- ✅ APLICADO el 2026-10-15, encabezado corregido en el MISMO movimiento.
--
-- ## Para qué
--
-- La Oficina de Innovación emite la certificación laboral del contratista, y
-- ese documento imprime las obligaciones NUMERADAS, una por una. Lo pidieron por
-- escrito: «es un documento con efectos para la persona». SECOP no publica las
-- obligaciones como campo —se revisaron las 19 claves del contrato— y lo más
-- cercano, el objeto contractual, es un párrafo que no sirve para eso.
--
-- Sí están en el estudio previo, que SÍ se publica, en PDF.
--
-- ## Lo que se midió antes de escribir esto (2026-10-15, sobre los 5.558)
--
--     año    contratos con estudio previo publicado
--     2020        0 / 362     0,0 %
--     2021        0 / 532     0,0 %
--     2022        0 / 788     0,0 %
--     2023        0 / 665     0,0 %
--     2024    1.031 / 1.135  90,8 %
--     2025    1.012 / 1.184  85,5 %
--     2026      720 /   872  82,6 %
--     ─────────────────────────────
--     2024-2026  2.763 / 3.191  86,6 %   ·   total 2.773 / 5.558  49,9 %
--
-- **De 2020 a 2023 es CERO, y no por falta nuestra**: de esos años solo se
-- publicó el expediente POST-contractual —actas de cierre, liquidaciones,
-- certificados, CDP, CRP, designaciones—, 2,6 archivos por proceso contra 51 en
-- 2025-2026. El estudio previo de esas vigencias no está en ningún dataset.
-- Esos contratos van a quedar con la lista vacía y su motivo, que es
-- exactamente lo que pidió quien consume: «si el dato no existe, preferimos el
-- campo vacío; un certificado con obligaciones copiadas de otro contrato sería
-- peor que uno que dice No registradas».
--
-- Hay 7.332 archivos de estudio previo sobre 2.773 procesos —3,5 por proceso—,
-- así que la VERSIÓN importa: se guarda la más reciente por `fecha_carga` y las
-- demás quedan registradas para poder auditar cuál se usó.
--
-- ## Dos cosas que descubrió la prueba de extracción
--
-- 1. **La URL de descarga da 403 con el agente por defecto.** El Application
--    Gateway de Azure que sirve los archivos de SECOP rechaza a curl; con un
--    User-Agent de navegador responde 200 y el tamaño coincide al byte con el
--    que declara el dataset. La ingesta lo manda y lo dice en su encabezado.
--
-- 2. **La calidad del texto varía y hay que medirla por documento.** Medido
--    sobre 6 PDFs: los estudios previos de CPS salen limpios —1,7 % a 2,2 % de
--    letras sueltas sospechosas— pero un convenio de 40 páginas llegó a 4,6 %,
--    con palabras partidas («verac idad», «docume ntos»). Eso se imprimiría así
--    en el certificado, así que cada documento guarda su métrica y el que no
--    pase la compuerta NO publica lista: publica su motivo y la URL para que
--    alguien la transcriba a mano.
--
--    La primera métrica que usé contaba TODAS las letras sueltas y daba 10 %,
--    lo que me hizo concluir que el texto era inservible. Era falso: 528 de
--    las 668 eran «y», «a», «o», «e», «u», que son palabras del español. La
--    métrica buena excluye esas cinco.
--
-- Rollback: rollback_036_obligaciones_estudio_previo.sql

BEGIN;

-- ── 1 · El documento del que salen ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS secop_documento (
    id                  bigserial PRIMARY KEY,
    proceso             varchar(60) NOT NULL,
    id_documento        bigint      NOT NULL,
    -- El contrato que declara el dataset de archivos. Puede venir vacío, y puede
    -- NO ser uno de los nuestros: un proceso adjudica varios contratos.
    numero_contrato     varchar(60),
    clase               varchar(40) NOT NULL,
    nombre_archivo      text,
    extension           varchar(20),
    bytes               bigint,
    fecha_carga         timestamptz,
    url_descarga        text,
    fuente              varchar(40)  NOT NULL,
    -- Estado de la extracción. `pendiente` es lo que todavía no se ha bajado.
    extraccion_estado   varchar(24)  NOT NULL DEFAULT 'pendiente',
    extraccion_motivo   text,
    extraccion_fecha    timestamptz,
    paginas             integer,
    caracteres          integer,
    -- La métrica de calidad: % de letras sueltas que NO son «y a o e u».
    calidad_pct         numeric(6, 2),
    -- El texto de la sección, tal como se extrajo. Es el respaldo auditable de
    -- cada obligación publicada; sin él, la lista es una afirmación sin fuente.
    seccion_texto       text,
    seccion_encabezado  text,
    hash_fila           varchar(64),
    synced_at           timestamptz DEFAULT now(),
    CONSTRAINT ck_doc_extraccion CHECK (extraccion_estado IN
        ('pendiente', 'ok', 'sin_seccion', 'calidad_baja',
         'descarga_fallo', 'no_es_pdf', 'sin_texto', 'error'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_secop_documento
    ON secop_documento (proceso, id_documento);
CREATE INDEX IF NOT EXISTS idx_secop_documento_proceso
    ON secop_documento (proceso, clase, fecha_carga DESC);
CREATE INDEX IF NOT EXISTS idx_secop_documento_pendiente
    ON secop_documento (extraccion_estado) WHERE extraccion_estado = 'pendiente';

COMMENT ON COLUMN secop_documento.calidad_pct IS
    'Porcentaje de tokens de una sola letra que NO son «y a o e u» (que sí son '
    'palabras del español). Mide lo roto del texto extraído: los estudios '
    'previos de CPS dan 1,7-2,2 %; un convenio con palabras partidas dio 4,6 %.';

-- ── 2 · Las obligaciones ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS secop_obligacion (
    id              bigserial PRIMARY KEY,
    proceso         varchar(60) NOT NULL,
    documento_id    bigint      NOT NULL REFERENCES secop_documento(id)
                                ON DELETE CASCADE,
    numero          integer     NOT NULL,
    descripcion     text        NOT NULL,
    -- De dónde salió, literal, para que nadie tenga que creernos.
    metodo          varchar(40) NOT NULL,
    synced_at       timestamptz DEFAULT now(),
    CONSTRAINT ck_obligacion_numero CHECK (numero > 0),
    CONSTRAINT ck_obligacion_texto  CHECK (length(trim(descripcion)) > 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_secop_obligacion
    ON secop_obligacion (documento_id, numero);
CREATE INDEX IF NOT EXISTS idx_secop_obligacion_proceso
    ON secop_obligacion (proceso);

COMMENT ON TABLE secop_obligacion IS
    'Obligaciones específicas leídas del estudio previo. NO se derivan de '
    'contratos parecidos ni se completan: lo que no se pudo leer no está acá, y '
    'el motivo queda en secop_documento.extraccion_motivo.';

COMMIT;
