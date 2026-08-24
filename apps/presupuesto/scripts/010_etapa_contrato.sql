-- 010_etapa_contrato.sql — la etapa contractual, que no existía en ninguna parte.
--
-- POR QUÉ HACE FALTA DDL (medido 2026-08-23, no supuesto):
--   · `contrato` tiene 18 columnas y NINGUNA es etapa.
--   · Barrido de las 268 tablas del esquema por `etapa|fase|estado|liquidac|
--     sanciona`: 19 columnas, ninguna cuelga de un contrato.
--   · Por `incumpl|multa|sancion|caducid`: CERO en todo el esquema. O sea que
--     «Sancionatorio» literalmente no tenía dónde vivir.
--   · `fase_proyecto` existe pero es de PROYECTO y son 3 filas (Planeación /
--     Ejecución / Cierre), no las cuatro que pide el alcalde. Su única FK es
--     `presupuesto_tiempo`, con 0 filas. Meterle una cuarta fila contaminaría
--     un catálogo de otra cosa.
--   · `secop_contrato.estado_contrato` está poblado 3.072/3.072, pero de
--     nuestros 25 contratos: 20 dicen «Modificado» —que significa que hubo
--     otrosí, no una etapa—, 2 «En ejecución», 1 «Cerrado», 1 «Suspendido».
--     Cero en Formulación, Liquidación y Sancionatorio. No se puede derivar.
--
-- Se capturan las TRES columnas juntas, no solo la etapa: sin fecha ni usuario
-- no hay auditoría, y este dato lo escribe una persona sobre información
-- contractual. Saber quién marcó qué y cuándo es parte del dato.

BEGIN;

-- Catálogo propio. `orden` manda en el stepper; no se infiere del código.
CREATE TABLE IF NOT EXISTS etapa_contrato (
    codigo      smallint     PRIMARY KEY,
    nombre      varchar(30)  NOT NULL UNIQUE,
    orden       smallint     NOT NULL,
    descripcion text
);

INSERT INTO etapa_contrato (codigo, nombre, orden, descripcion) VALUES
    (1, 'Formulación',   1, 'Estructuración y trámite previo a la firma.'),
    (2, 'Ejecución',     2, 'El contrato está en curso.'),
    (3, 'Liquidación',   3, 'Cerrado el objeto, en trámite de liquidación.'),
    (4, 'Sancionatorio', 4, 'Con proceso de incumplimiento, multa o caducidad.')
ON CONFLICT (codigo) DO NOTHING;

-- Las tres, aditivas y nullable: NULL = «pendiente de registrar», que es lo
-- que la pantalla debe decir. Nunca se asume «Ejecución» por defecto.
ALTER TABLE contrato
    ADD COLUMN IF NOT EXISTS etapa_codigo     smallint,
    ADD COLUMN IF NOT EXISTS etapa_fecha      timestamptz,
    ADD COLUMN IF NOT EXISTS etapa_usuario_id integer;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                   WHERE constraint_name = 'contrato_etapa_codigo_fkey') THEN
        ALTER TABLE contrato
            ADD CONSTRAINT contrato_etapa_codigo_fkey
            FOREIGN KEY (etapa_codigo) REFERENCES etapa_contrato(codigo)
            ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                   WHERE constraint_name = 'contrato_etapa_usuario_fkey') THEN
        ALTER TABLE contrato
            ADD CONSTRAINT contrato_etapa_usuario_fkey
            FOREIGN KEY (etapa_usuario_id) REFERENCES usuario(id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_contrato_etapa ON contrato (etapa_codigo);

COMMIT;
