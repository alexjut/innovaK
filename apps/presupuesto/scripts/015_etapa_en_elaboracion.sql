-- 015_etapa_en_elaboracion.sql — la etapa que va ANTES de todas.
--
-- Un contrato «en elaboración» es uno que el área está estructurando y que
-- todavía NO se ha publicado en SECOP. Hoy esa realidad no tenía dónde vivir:
-- el catálogo arrancaba en Formulación, que ya supone un proceso en marcha.
--
-- POR QUÉ ES UNA SOLA FILA Y NO UN REDISEÑO
--
-- El DDL 010 separó `codigo` de `orden` a propósito, y su comentario lo decía:
-- «`orden` manda en el stepper: no se infiere del código ni del nombre».
-- Éste es exactamente el caso que esa decisión anticipaba — una etapa nueva
-- que va PRIMERO pero cuyo código tiene que ser el siguiente libre, porque los
-- códigos 1..4 ya están escritos en `contrato.etapa_codigo`.
--
--     código 5  ← el siguiente libre; cambiar los otros reescribiría datos
--     orden  0  ← va antes de Formulación
--
-- El stepper del frontend ya es data-driven: lee el catálogo del servidor y
-- ordena por `orden`. Esta fila entra sola.
--
-- ADITIVA: una fila en un catálogo. No toca ninguna columna ni ningún dato.

BEGIN;

INSERT INTO etapa_contrato (codigo, nombre, orden, descripcion) VALUES
    (5, 'En elaboración', 0,
     'El área está estructurando el contrato. Todavía no se ha publicado en '
     'SECOP ni tiene número asignado.')
ON CONFLICT (codigo) DO NOTHING;

COMMIT;
