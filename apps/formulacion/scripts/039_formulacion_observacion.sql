-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║ 039 · La observación como entidad                                         ║
-- ╚══════════════════════════════════════════════════════════════════════════╝
--
-- ✅ APLICADO el 2026-10-15, encabezado corregido en el MISMO movimiento.
--    Respaldo del día: 13 h de antigüedad al aplicar.
--
-- ## El problema
--
-- Hoy «Con observaciones» es solo un ESTADO. No hay dónde guardar qué se
-- observó, en qué sección, quién lo dijo, ni si se respondió. El texto, si
-- acaso, va en el campo `observacion` de la auditoría del cambio de estado: una
-- sola cadena para todo lo que el revisor tenga que decir, sin sección, sin
-- requisito y sin forma de responder una cosa y no otra.
--
-- Con eso, «devolver con observaciones» es un gesto: el formulador recibe un
-- estado y un párrafo, y nadie puede comprobar después qué se corrigió.
--
-- Las Historias de Usuario entregadas lo piden textual:
--   · «Las observaciones pueden asociarse a secciones/campos.»
--   · «Permite marcar observaciones como atendidas sin eliminarlas.»
--   · «Registra trazabilidad completa.»
--
-- ## El ciclo, y por qué tiene cuatro estados y no dos
--
--     abierta      el revisor la escribió
--     respondida   el formulador contestó — NO la cierra él
--     atendida     el revisor aceptó la respuesta
--     desestimada  el revisor la retiró (se equivocó al observarla)
--
-- `respondida` existe para que cerrar no sea del mismo que responde. Si el
-- formulador pudiera marcar «atendida», la observación sería un trámite: se
-- responde cualquier cosa y se cierra sola. La separación es la misma que
-- gobierna las transiciones (DDL 037).
--
-- `desestimada` existe porque un revisor se equivoca, y la alternativa sería
-- borrar la observación — justo lo que las Historias prohíben. Retirarla
-- dejando el rastro es lo honesto.
--
-- ## Nunca se borra
--
-- No hay DELETE en el servicio y no debe haberlo. Una observación es la razón
-- por la que una formulación volvió atrás; borrarla deja el expediente diciendo
-- que el camino fue recto. Si una observación sobra, se DESESTIMA.
--
-- Rollback: rollback_039_formulacion_observacion.sql

BEGIN;

CREATE TABLE IF NOT EXISTS formulacion_observacion (
    id              bigserial PRIMARY KEY,
    formulacion_id  bigint      NOT NULL
                    REFERENCES formulacion(id) ON DELETE CASCADE,
    -- Dónde. La sección es el bloque del catálogo de requisitos
    -- (necesidad, tecnico, financiero, contractual, revision); el requisito y
    -- el campo son opcionales y cada vez más específicos.
    seccion         varchar(30),
    requisito_codigo varchar(40)
                    REFERENCES formulacion_requisito(codigo) ON DELETE SET NULL,
    campo           varchar(80),
    -- Qué, y de quién. El carril se guarda ADEMÁS del usuario: un usuario puede
    -- cambiar de rol, y entonces «quién observó esto» dejaría de poder
    -- responderse mirando sus grupos de hoy.
    texto           text        NOT NULL,
    autor_id        bigint      NOT NULL,
    autor_carril    varchar(30) NOT NULL,
    creado_en       timestamptz NOT NULL DEFAULT now(),
    -- La respuesta del formulador.
    respuesta       text,
    respondida_por_id bigint,
    respondida_en   timestamptz,
    -- El cierre, que es del revisor.
    estado          varchar(20) NOT NULL DEFAULT 'abierta',
    cerrada_por_id  bigint,
    cerrada_en      timestamptz,
    cierre_motivo   text,

    CONSTRAINT ck_obs_estado CHECK (estado IN
        ('abierta', 'respondida', 'atendida', 'desestimada')),
    CONSTRAINT ck_obs_texto CHECK (length(trim(texto)) >= 10),
    -- Una respondida tiene que traer la respuesta y su autor. Sin eso, el
    -- estado afirma que alguien contestó y no se puede saber qué dijo.
    CONSTRAINT ck_obs_respondida CHECK (
        estado <> 'respondida' OR
        (respuesta IS NOT NULL AND respondida_por_id IS NOT NULL
         AND respondida_en IS NOT NULL)),
    -- Una cerrada tiene que decir quién la cerró y cuándo.
    CONSTRAINT ck_obs_cerrada CHECK (
        estado NOT IN ('atendida', 'desestimada') OR
        (cerrada_por_id IS NOT NULL AND cerrada_en IS NOT NULL)),
    -- Y una desestimada tiene que decir POR QUÉ: retirar una observación sin
    -- motivo es indistinguible de borrarla.
    CONSTRAINT ck_obs_desestimada CHECK (
        estado <> 'desestimada' OR length(trim(coalesce(cierre_motivo,''))) >= 10)
);

CREATE INDEX IF NOT EXISTS idx_obs_formulacion
    ON formulacion_observacion (formulacion_id, estado);
-- Las abiertas son la consulta caliente: son las que trancan el reenvío.
CREATE INDEX IF NOT EXISTS idx_obs_pendientes
    ON formulacion_observacion (formulacion_id)
 WHERE estado IN ('abierta', 'respondida');

COMMENT ON TABLE formulacion_observacion IS
    'Las observaciones de una revisión. NUNCA se borran: una observación es la '
    'razón por la que una formulación volvió atrás, y borrarla deja el '
    'expediente diciendo que el camino fue recto. Lo que sobra se DESESTIMA, '
    'con motivo.';

COMMENT ON COLUMN formulacion_observacion.autor_carril IS
    'El carril desde el que se observó, guardado además del usuario: un usuario '
    'puede cambiar de rol, y entonces «quién observó esto» dejaría de poder '
    'responderse mirando sus grupos de hoy.';

COMMIT;
