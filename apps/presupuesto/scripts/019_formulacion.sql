-- 019_formulacion.sql — el dominio FORMULACIÓN.
--
-- ⚠️ NO APLICADO. Requiere aprobación explícita de Alex (Constitución VII) y
-- backup < 24 h. Ensayado en un postgres:16-alpine desechable.
--
-- QUÉ ES. Lo que el área prepara ANTES de que exista el contrato. Decisión del
-- 2026-08-26/27, en brain/Decisiones/2026-08-27-formulacion-dominio-propio.md
-- y specs/004-formulacion/plan.md.
--
-- EL ANCLA ES LA ACTIVIDAD, no la meta. Palabras de Alex: «la formulación es de
-- contrato, o como lo llamamos acá, actividades». Y una formulación POR
-- VIGENCIA: `actividad_plan` se queda como el enunciado estable del plan —se
-- escribe una vez— y cada año cuelga de ella una formulación.
--
-- EL CASO QUE FIJA EL MODELO es el Banco de Iniciativas de Deporte
-- (`actividad_plan` #108): indicador de 280 colectivos, 24 inscripciones
-- evaluadas, y CERO contratos porque no está en SECOP — el contrato se está
-- armando. Es exactamente lo que estas tablas tienen que poder guardar.
--
-- TODO ADITIVO: siete tablas nuevas y ninguna columna tocada. Nada de lo que ya
-- existe cambia de forma ni de contenido.
--
-- IDEMPOTENTE: correrlo dos veces no rompe ni duplica (IF NOT EXISTS en tablas
-- e índices, ON CONFLICT DO NOTHING en las siembras). Es la convención de los
-- DDL de este repo y no es cosmética: en una base compartida, «¿ya corrió?» es
-- una pregunta que se hace tarde y con miedo.

BEGIN;

-- ── 1 · El catálogo de estados ───────────────────────────────────────
-- En TABLA y no en `choices` de Django, porque `choices` NO valida en save() y
-- las columnas de estado del repo son texto sin CHECK: hoy un `.update()` o un
-- script puede escribir cualquier cadena. Medido: el Banco de Iniciativas
-- permite saltar de «borrador» a «validada» sin pasar por «enviada».
CREATE TABLE IF NOT EXISTS formulacion_estado (
    codigo               smallint PRIMARY KEY,
    nombre               varchar(40) NOT NULL UNIQUE,
    orden                smallint NOT NULL UNIQUE,
    descripcion          text,
    -- Estado terminal: de acá no se sale (ni hacia adelante ni hacia atrás).
    es_final             boolean NOT NULL DEFAULT false,
    -- Mientras sea true, la formulación NO puede pasar a contratación.
    bloquea_contratacion boolean NOT NULL DEFAULT true
);

INSERT INTO formulacion_estado (codigo, nombre, orden, descripcion, es_final, bloquea_contratacion) VALUES
 (1, 'Borrador',                 1, 'Creada, todavía sin diligenciar.',                                false, true),
 (2, 'En elaboración',           2, 'El área está construyendo la formulación.',                        false, true),
 (3, 'En formulación',           3, 'Completando requisitos técnicos, financieros y administrativos.',  false, true),
 (4, 'Pendiente de información', 4, 'Faltan elementos obligatorios para poder revisarla.',              false, true),
 (5, 'En revisión',              5, 'Enviada a revisión.',                                              false, true),
 (6, 'Con observaciones',        6, 'La revisión dejó correcciones pendientes.',                        false, true),
 (7, 'Subsanando',               7, 'El área está resolviendo las observaciones.',                      false, true),
 (8, 'Aprobada',                 8, 'Cumple los requisitos internos.',                                  false, true),
 (9, 'Lista para contratación',  9, 'Terminó la formulación y puede continuar.',                        false, false),
 (10,'Cancelada',               10, 'No continuará el proceso. Nada se borra: queda con su motivo.',    true,  true)
ON CONFLICT (codigo) DO NOTHING;

-- ── 2 · Las transiciones válidas, en tabla ───────────────────────────
-- El grafo es DATO, no un diccionario en Python. Este repo no tiene ni una
-- máquina de estados: sus cinco intentos validan la ACCIÓN pero nunca el
-- estado de ORIGEN. La guarda tiene que estar en el servicio Y en el dato.
CREATE TABLE IF NOT EXISTS formulacion_transicion (
    origen  smallint NOT NULL REFERENCES formulacion_estado(codigo),
    destino smallint NOT NULL REFERENCES formulacion_estado(codigo),
    PRIMARY KEY (origen, destino),
    CONSTRAINT ck_formulacion_transicion_distinta CHECK (origen <> destino)
);

INSERT INTO formulacion_transicion (origen, destino) VALUES
 (1,2),                       -- Borrador → En elaboración
 (2,3), (2,4),                -- En elaboración → En formulación / Pendiente
 (3,4), (3,5),                -- En formulación → Pendiente / En revisión
 (4,3),                       -- Pendiente → En formulación (llegó lo que faltaba)
 (5,6), (5,8),                -- En revisión → Con observaciones / Aprobada
 (6,7),                       -- Con observaciones → Subsanando
 (7,5),                       -- Subsanando → En revisión
 (8,9),                       -- Aprobada → Lista para contratación
 (8,6),                       -- Aprobada → Con observaciones (se reabre)
 (1,10), (2,10), (3,10), (4,10), (5,10), (6,10), (7,10), (8,10)   -- cancelar
ON CONFLICT (origen, destino) DO NOTHING;

-- ── 3 · La formulación ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS formulacion (
    id                  bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,

    -- El ancla. NOT NULL las dos: una formulación sin actividad o sin año no
    -- se puede reportar, y reportar es su razón de existir.
    actividad_plan_id   bigint  NOT NULL REFERENCES actividad_plan(id),
    vigencia            integer NOT NULL REFERENCES vigencia(codigo),

    -- Denormalizado A PROPÓSITO: `aplicar_subgrupo(qs, user, "subgrupo_id")`
    -- ya existe y con esto el scope funciona sin motor nuevo ni JOIN extra.
    subgrupo_id         integer NOT NULL REFERENCES subgrupo(id),

    objeto              text NOT NULL,
    descripcion         text,
    valor_estimado      numeric(18,4),

    -- Quién RESPONDE por ella. Es dato, no permiso: quién puede tocarla lo
    -- decide el scope + el rol, que ya existen y no se tocan.
    responsable_funcionario_id integer REFERENCES funcionario(id) ON DELETE SET NULL,

    -- El estado, con su fecha y su autor. El mismo patrón de tres columnas que
    -- ya usan contrato.etapa_* y forma_pago_*: sobre información contractual,
    -- un dato sin fecha ni autor no se puede defender.
    estado_codigo       smallint NOT NULL REFERENCES formulacion_estado(codigo),
    estado_fecha        timestamptz NOT NULL,
    estado_usuario_id   integer REFERENCES usuario(id) ON DELETE SET NULL,

    creado_en           timestamptz NOT NULL,
    creado_usuario_id   integer REFERENCES usuario(id) ON DELETE SET NULL,
    actualizado_en      timestamptz,

    -- Cancelar no borra. Los tres van juntos o ninguno.
    cancelado_en        timestamptz,
    cancelado_usuario_id integer REFERENCES usuario(id) ON DELETE SET NULL,
    cancelado_motivo    text,

    -- Una actividad se formula UNA vez por vigencia (decisión de Alex,
    -- 2026-08-27). Si algún año hiciera falta partirla en dos procesos, esto
    -- es lo primero que hay que revisar.
    CONSTRAINT uq_formulacion_actividad_vigencia UNIQUE (actividad_plan_id, vigencia),
    CONSTRAINT ck_formulacion_cancelada_completa CHECK (
        cancelado_en IS NULL
        OR (cancelado_motivo IS NOT NULL AND cancelado_usuario_id IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_formulacion_subgrupo  ON formulacion (subgrupo_id, vigencia);
CREATE INDEX IF NOT EXISTS idx_formulacion_estado    ON formulacion (estado_codigo);
CREATE INDEX IF NOT EXISTS idx_formulacion_actividad ON formulacion (actividad_plan_id);

COMMENT ON TABLE formulacion IS
    'Lo que el área prepara ANTES de que exista el contrato. Cuelga de la '
    'actividad del plan y de la vigencia. El caso que fijó el modelo es el '
    'Banco de Iniciativas de Deporte: expediente completo y cero contratos.';

-- ── 4 · El checklist configurable ────────────────────────────────────
-- En TABLA y no en columnas ni en listas de Python, y la prueba está dentro de
-- este mismo repo: el catálogo de anexos del Banco vive en TRES sitios —el
-- CHECK de la base con 17 valores, ANEXOS con 14 claves y TIPO_CHOICES con 8—
-- y ya divergieron.
CREATE TABLE IF NOT EXISTS formulacion_requisito (
    codigo          varchar(40) PRIMARY KEY,
    nombre          varchar(140) NOT NULL,
    descripcion     text,
    bloque          varchar(30) NOT NULL,
    orden           smallint NOT NULL,
    -- SIN PESO, a propósito: la completitud es plana y el rigor lo pone
    -- `bloquea`. Así se cumple «al 90 % y seguir bloqueada» sin contradecir la
    -- decisión escrita el 2026-08-24 («cualquier ponderación es una opinión
    -- disfrazada de número»).
    obligatorio     boolean NOT NULL DEFAULT true,
    bloquea         boolean NOT NULL DEFAULT false,
    exige_evidencia boolean NOT NULL DEFAULT false,
    activo          boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS formulacion_requisito_cumplido (
    id               bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    formulacion_id   bigint NOT NULL REFERENCES formulacion(id) ON DELETE CASCADE,
    requisito_codigo varchar(40) NOT NULL REFERENCES formulacion_requisito(codigo),
    -- Los MISMOS cuatro estados del motor de completitud del expediente, y
    -- `no_aplica` queda FUERA del denominador por la misma razón que allá:
    -- es la diferencia entre medir y castigar.
    estado           varchar(12) NOT NULL,
    observacion      text,
    documento_id     bigint,
    fecha            timestamptz,
    usuario_id       integer REFERENCES usuario(id) ON DELETE SET NULL,
    CONSTRAINT uq_formulacion_requisito UNIQUE (formulacion_id, requisito_codigo),
    CONSTRAINT ck_formulacion_requisito_estado
        CHECK (estado IN ('ok', 'pendiente', 'sin_dato', 'no_aplica'))
);

CREATE INDEX IF NOT EXISTS idx_form_requisito_formulacion ON formulacion_requisito_cumplido (formulacion_id);

-- ── 5 · Los documentos soporte ───────────────────────────────────────
-- No hay tabla genérica de documentos en el repo: cada dominio tiene la suya.
-- Se calca el esqueleto de `festival_archivo`, que ya contempla Mongo (activo)
-- y OneDrive (apagado por credenciales, se cablea y espera).
CREATE TABLE IF NOT EXISTS formulacion_documento (
    id               bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    formulacion_id   bigint NOT NULL REFERENCES formulacion(id) ON DELETE CASCADE,
    tipo             varchar(40),
    mongo_id         varchar(48),
    onedrive_item_id varchar(120),
    nombre_archivo   text NOT NULL,
    mime             varchar(120),
    tamano_bytes     bigint,
    subido_por_id    integer REFERENCES usuario(id) ON DELETE SET NULL,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_form_documento_formulacion ON formulacion_documento (formulacion_id);

DO $$
BEGIN
    ALTER TABLE formulacion_requisito_cumplido
        ADD CONSTRAINT formulacion_requisito_documento_fk
        FOREIGN KEY (documento_id) REFERENCES formulacion_documento(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL;   -- ya estaba: correr dos veces no rompe
END $$;

-- ── 6 · El puente al contrato: N:M, y la data obliga ─────────────────
-- No es una columna en `contrato`. Medido: el contrato 98 toca SIETE
-- actividades del plan, y si formulación = actividad, ese contrato nace de
-- siete formulaciones. Al revés también: una actividad puede dar más de un
-- contrato (los #124 y #125 tienen dos cada uno).
CREATE TABLE IF NOT EXISTS formulacion_contrato (
    formulacion_id bigint NOT NULL REFERENCES formulacion(id) ON DELETE CASCADE,
    contrato_id    integer NOT NULL REFERENCES contrato(id) ON DELETE CASCADE,
    ligado_en      timestamptz NOT NULL DEFAULT now(),
    ligado_por_id  integer REFERENCES usuario(id) ON DELETE SET NULL,
    PRIMARY KEY (formulacion_id, contrato_id)
);

CREATE INDEX IF NOT EXISTS idx_formulacion_contrato_contrato ON formulacion_contrato (contrato_id);

COMMENT ON TABLE formulacion_contrato IS
    'De qué formulación nació un contrato, y en qué contratos terminó una '
    'formulación. N:M porque los datos lo exigen: el contrato 98 toca siete '
    'actividades del plan.';

COMMIT;
