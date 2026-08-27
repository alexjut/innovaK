-- 018_etapas_fuera_del_contrato.sql — «En elaboración» y «Formulación» dejan
-- de ser etapas del contrato, y el número vuelve a ser obligatorio.
--
-- ⚠️ NO APLICAR TODAVÍA. Este script sólo debe correr CUANDO EL DOMINIO
-- FORMULACIÓN YA EXISTA (specs/004-formulacion/plan.md, Bloque 3). Antes de
-- eso, el contrato que aún no tiene número se quedaría sin dónde vivir.
--
-- POR QUÉ. Las dos etapas ocurren ANTES de que el contrato exista, así que no
-- son su ciclo de vida. Decisión del 2026-08-26, escrita en
-- brain/Decisiones/2026-08-27-formulacion-dominio-propio.md.
--
-- QUÉ SE MIDIÓ ANTES DE ESCRIBIRLO (2026-08-26 / 2026-08-27):
--
--   · `etapa_codigo` está NULL en los 25 contratos. Ninguno usa la 5 ni la 1:
--     no hay un solo dato que migrar.
--   · Una sola FK entrante en todo el esquema (`contrato_etapa_codigo_fkey`),
--     y es ON DELETE SET NULL — de ahí la guarda de abajo.
--   · Ningún literal 5 ni 1 cableado como código de etapa en el backend: los
--     dos endpoints validan contra el catálogo y empiezan a rechazarlos solos.
--   · UNIQUE (orden) es DEFERRABLE y queda satisfecho con 2,3,4. NO hay que
--     reordenar; los huecos son inocuos porque el stepper compara relativo.
--   · `contrato_numero`: 25 de 25 con número, 0 NULL. El modelo Django nunca
--     dejó de exigirlo, así que la relajación del 016 no la usó nadie.
--   · Con número NULL, `uq_contrato_tripleta` deja de proteger: PostgreSQL
--     trata cada NULL como distinto (indnullsnotdistinct = false). O sea que
--     el 016 apagó la unicidad justo en las filas para las que se hizo.
--
-- LAS DOS GUARDAS NO SON CORTESÍA. Sin la primera, un DELETE pelado pasa
-- limpio y deja con `etapa_codigo` NULL a los contratos que la usaran,
-- indistinguibles de los que nunca la tuvieron. Sin la segunda, el ALTER
-- revienta con un error de restricción que no explica nada.

BEGIN;

-- ── 1 · Las dos etapas salen del catálogo ────────────────────────────
DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM contrato WHERE etapa_codigo IN (5, 1);
    IF n > 0 THEN
        RAISE EXCEPTION
            'No se pueden retirar «En elaboración» y «Formulación»: % contrato(s) '
            'las usan. Migralos primero al dominio Formulación.', n;
    END IF;
END $$;

DELETE FROM etapa_contrato WHERE codigo IN (5, 1);

COMMENT ON TABLE etapa_contrato IS
    'Etapas del CICLO DE VIDA DEL CONTRATO. Lo previo a que el contrato exista '
    '—elaboración, formulación, estudios, revisiones— NO va acá: es el dominio '
    'Formulación (spec 004).';

-- ── 2 · El número vuelve a ser obligatorio ───────────────────────────
DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM contrato WHERE contrato_numero IS NULL;
    IF n > 0 THEN
        RAISE EXCEPTION
            'Hay % contrato(s) sin número. Un contrato sin número ya no existe '
            'en este modelo: lo que no tiene número es una Formulación.', n;
    END IF;
END $$;

ALTER TABLE contrato ALTER COLUMN contrato_numero SET NOT NULL;

COMMENT ON COLUMN contrato.contrato_numero IS
    'Obligatorio. Un contrato sin número no es un contrato: es una Formulación '
    '(spec 004). Revierte el DDL 016, cuya justificación —la etapa «En '
    'elaboración»— dejó de existir.';

COMMIT;
