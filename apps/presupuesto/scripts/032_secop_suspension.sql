-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║ 032 · secop_suspension — el espejo del dataset DEDICADO de suspensiones  ║
-- ╚══════════════════════════════════════════════════════════════════════════╝
--
-- ✅ APLICADO el 2026-10-13, y este encabezado se corrigió en el MISMO
--    movimiento. Siete scripts de este repo quedaron mintiendo por no hacerlo,
--    y eso costó que llegara un encargo para construir un módulo que ya
--    existía.
--
-- ## Por qué hace falta una tabla propia
--
-- `secop_modificacion` trae el `tipo` INVERTIDO en el par
-- suspensión/reactivación. Probado fila contra fila, emparejando por contrato
-- Y fecha de aprobación, el 2026-10-13: donde nuestro espejo dice SUSPENSIoN,
-- el dataset oficial dice «Reanudacion», y el propio texto del propósito lo
-- confirma —«Se procede a REINICIAR el Contrato CPS-032-2024»—. Seis de seis.
--
-- Hasta hoy la API publicaba ese eje SIN CLASIFICAR y con su advertencia:
-- fechar una suspensión con ese `tipo` la fecharía el día en que el contrato se
-- reactivó, en un documento con efectos jurídicos. Con esta tabla YA SE
-- CLASIFICA —398 filas de 432, el 92,1 %—, y las 34 restantes son las fechas
-- en que el mismo contrato tiene dos modificaciones del par: ahí el acto
-- oficial no dice a cuál pertenece y se declara la ambigüedad en vez de
-- escoger. La clasificación general de modificaciones pasó de 64,8 % a 72,0 %.
--
-- El dataset `u99c-7mfm` («SECOP II - Suspensiones de Contratos») lo resuelve:
-- 860.898 filas con solo DOS tipos limpios —Suspension 464.444 y Reanudacion
-- 396.454— y la misma llave `id_contrato` que ya usamos.
--
-- ## Las cifras de Kennedy, medidas antes de escribir esto
--
--     filas que devuelve para nuestros 3.211 contratos ... 5.668
--     de ellas, duplicados IDÉNTICOS byte a byte ......... 4.286  (75,6 %)
--     filas distintas .................................... 1.382
--     ACTOS reales (ver la llave de abajo) ...............   941
--       suspensiones ..................................... 567
--       reanudaciones .................................... 374
--     contratos cubiertos ................................   352
--     contratos que vemos HOY con ese par ................   201
--     ganancia ...........................................  +151 contratos
--
-- Ingerirlo sin deduplicar guardaría 5.668 filas y cualquiera que contara
-- actos de suspensión obtendría CUATRO VECES el número real.
--
-- ## La llave natural, y por qué es ésta
--
-- El dataset NO trae identificador de fila. Medido sobre las 1.382 distintas:
--
--     (contrato, tipo, fecha_aprobacion) ............ 940 claves  → NO sirve
--     + fecha_creacion .............................. 941 claves  → ésta
--
-- Los 383 grupos con varias filas difieren casi solo en el propósito (382 de
-- 383): son VARIANTES DEL MISMO ACTO que el origen publica repetido, no actos
-- distintos el mismo día. Se comprobó leyéndolas: tres con el mismo texto y una
-- con «No definido».
--
-- Por eso el comando se queda con el propósito MÁS INFORMATIVO de cada acto.
-- Con esa regla solo 8 actos (0,9 %) quedan sin texto útil; tomando una fila
-- cualquiera serían 384.
--
-- Aditivo. No toca ninguna tabla existente. Idempotente.

BEGIN;

CREATE TABLE IF NOT EXISTS secop_suspension (
    id                     BIGSERIAL PRIMARY KEY,
    id_contrato            VARCHAR(60)  NOT NULL,
    -- El literal del origen, para poder contrastar campo por campo con
    -- datos.gov.co. Es el sentido de un espejo.
    tipo_origen            VARCHAR(40)  NOT NULL,
    -- Nuestro código estable. El origen ya cambió una grafía antes (la Ó de
    -- REACTIVACIoN) y cablearse al literal rompe al consumidor cada vez.
    tipo_codigo            VARCHAR(40)  NOT NULL,
    fecha_creacion         DATE,
    fecha_aprobacion       DATE,
    -- El acto descrito en prosa. Es lo que permite auditar la clasificación:
    -- «Se procede a reiniciar el Contrato…» se lee y se comprueba.
    proposito              TEXT,
    contrato_fecha_inicio  DATE,
    contrato_fecha_fin     DATE,
    -- Cuántas filas del origen se colapsaron en este acto. No es adorno: si
    -- mañana sube a cientos, el origen cambió de comportamiento y hay que
    -- mirarlo antes de confiar en el conteo.
    filas_origen           INTEGER      NOT NULL DEFAULT 1,
    hash_fila              VARCHAR(64),
    fuente                 VARCHAR(40)  NOT NULL DEFAULT 'u99c-7mfm',
    synced_at              TIMESTAMPTZ  NOT NULL DEFAULT now(),

    -- Solo dos tipos, y se exige: si el origen inventa un tercero, la ingesta
    -- falla en vez de guardarlo en silencio.
    CONSTRAINT ck_secop_suspension_tipo
        CHECK (tipo_codigo IN ('SUSPENSION', 'REANUDACION'))
);

-- LA LLAVE NATURAL. Sin esto, 5.668 filas entran como 5.668 actos.
-- `COALESCE` en las fechas porque un NULL no se compara en un índice único, y
-- una llave natural que admite nulos es justo la que ya duplicó filas en el CRP
-- (ver DDL 028).
CREATE UNIQUE INDEX IF NOT EXISTS uq_secop_suspension_acto
    ON secop_suspension (
        id_contrato, tipo_codigo,
        COALESCE(fecha_creacion,   DATE '1900-01-01'),
        COALESCE(fecha_aprobacion, DATE '1900-01-01')
    );

CREATE INDEX IF NOT EXISTS idx_secop_suspension_contrato
    ON secop_suspension (id_contrato);
-- Para emparejar suspensión con su reanudación por orden cronológico.
CREATE INDEX IF NOT EXISTS idx_secop_suspension_crono
    ON secop_suspension (id_contrato, COALESCE(fecha_aprobacion, fecha_creacion));

COMMIT;

-- Comprobación posterior sugerida:
--   SELECT tipo_codigo, COUNT(*) FROM secop_suspension GROUP BY 1;
--     → SUSPENSION 567, REANUDACION 374  (al día de hoy)
