-- 016_contrato_numero_opcional.sql — el número deja de ser obligatorio.
--
-- POR QUÉ. Un contrato «en elaboración» (etapa 5, DDL 015) todavía NO tiene
-- número: se asigna al firmar. Hoy `contrato_numero` es NOT NULL, así que
-- registrar uno exigiría inventarle un número provisional — y un número
-- inventado sobre información contractual es exactamente lo que la
-- Constitución I prohíbe. Un dato que no existe se dice ausente, no se rellena.
--
-- QUÉ SE MIDIÓ ANTES DE ESCRIBIRLO (2026-08-26):
--
--   · 57 usos de `contrato_numero` en el backend. Todos son SELECT, ORDER BY o
--     interpolación en mensajes: ninguno rompe con NULL.
--   · La conciliación con SECOP YA lo contempla: `_EN_INNOVAK_SQL` tiene
--     `WHERE ci.contrato_numero IS NOT NULL`. Un contrato sin número
--     simplemente no empata, que es lo correcto — todavía no está publicado.
--   · NO hay índice ni constraint UNIQUE sobre (contrato_numero, vigencia).
--     Verificado contra pg_indexes y pg_constraint.
--   · Los 25 contratos existentes tienen número. Ninguno se toca.
--
-- ADITIVA EN EL SENTIDO QUE IMPORTA: relaja una restricción, no borra ni
-- transforma datos. Es el único DDL de esta fase que modifica una columna
-- existente, y por eso lleva la medición completa escrita arriba.
--
-- SOBRE EL ROLLBACK: volver a NOT NULL sólo funciona si no quedó ningún NULL.
-- El script de vuelta lo comprueba y lo dice, en vez de fallar con un error de
-- restricción que no explica nada.

BEGIN;

ALTER TABLE contrato ALTER COLUMN contrato_numero DROP NOT NULL;

COMMENT ON COLUMN contrato.contrato_numero IS
    'NULL mientras el contrato está en elaboración: el número se asigna al '
    'firmar. La conciliación con SECOP ignora los que no lo tienen.';

COMMIT;
