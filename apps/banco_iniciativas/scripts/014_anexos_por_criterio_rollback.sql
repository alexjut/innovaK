-- Rollback del 014 · vuelve el CHECK de `tipo` a los 8 valores originales.
--
-- ⚠️ Si ya se radicaron inscripciones con los tipos nuevos, este rollback
-- FALLA (el CHECK no puede crearse mientras existan filas que lo violen), que
-- es el comportamiento correcto: primero hay que decidir qué se hace con esos
-- soportes. Para ver si los hay:
--
--   SELECT tipo, count(*) FROM inscripcion_banco_anexo
--    WHERE tipo NOT IN ('soporte_legal','cedula_representante','rut',
--                       'reconocimiento_deportivo','aval_sectorial','firma',
--                       'complementario','consolidado')
--    GROUP BY tipo;

BEGIN;

ALTER TABLE inscripcion_banco_anexo
    DROP CONSTRAINT IF EXISTS ck_insc_banco_anexo_tipo;

ALTER TABLE inscripcion_banco_anexo
    ADD CONSTRAINT ck_insc_banco_anexo_tipo CHECK (
        tipo IN (
            'soporte_legal',
            'cedula_representante',
            'rut',
            'reconocimiento_deportivo',
            'aval_sectorial',
            'firma',
            'complementario',
            'consolidado'
        )
    );

COMMIT;
