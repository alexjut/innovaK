-- rollback_018_etapas_fuera_del_contrato.sql — devuelve las dos etapas al
-- catálogo y vuelve a permitir contratos sin número.
--
-- Los textos de `descripcion` son los originales del DDL 010 (código 1) y del
-- 015 (código 5), no una reescritura: un rollback que cambia el dato no es un
-- rollback.
--
-- El `orden` 0 y 1 quedan libres al retirarlas, así que el UNIQUE (orden) —que
-- además es DEFERRABLE— no estorba al reinsertarlas.

BEGIN;

INSERT INTO etapa_contrato (codigo, nombre, orden, descripcion) VALUES
    (5, 'En elaboración', 0,
     'El área está estructurando el contrato. Todavía no se ha publicado en '
     'SECOP ni tiene número asignado.'),
    (1, 'Formulación', 1,
     'Estructuración y trámite previo a la firma.')
ON CONFLICT (codigo) DO NOTHING;

ALTER TABLE contrato ALTER COLUMN contrato_numero DROP NOT NULL;

COMMENT ON COLUMN contrato.contrato_numero IS
    'NULL mientras el contrato está en elaboración: el número se asigna al '
    'firmar. La conciliación con SECOP ignora los que no lo tienen.';

COMMIT;
