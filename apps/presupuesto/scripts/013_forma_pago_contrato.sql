-- 013_forma_pago_contrato.sql — la forma de pago, en la tabla que ya existía.
--
-- QUÉ SE ENCONTRÓ ANTES DE ESCRIBIR ESTO (medido 2026-08-24):
--
--   · La tabla `forma_pago` YA EXISTE: (codigo integer, nombre text). Vacía.
--   · `crp.forma_pago_codigo` YA la referencia. `crp` también está vacía.
--   · `contrato` tiene 21 columnas y NINGUNA es forma de pago.
--   · `secop_contrato.modalidad` NO sirve: es modalidad de CONTRATACIÓN
--     («Mínima cuantía», «Licitación pública»), no forma de pago.
--
-- O sea que el catálogo y su referencia desde el CRP ya estaban diseñados. Lo
-- único que faltaba era que el CONTRATO pudiera apuntar ahí — que es lo que
-- hace falta hoy, porque `crp` está vacía y no hay acceso a BogData.
--
-- POR QUÉ LOS CÓDIGOS EMPIEZAN EN 901
--
-- La fuente de verdad de la forma de pago es BogData (decisión de Alex,
-- 2026-08-24). Hoy no hay acceso técnico, así que el área la captura mientras
-- tanto. Si se sembraran los códigos 1..5 y BogData después trajera SUS
-- códigos 1..N con otro significado, la corrupción sería silenciosa: mismo
-- número, distinto sentido, y nadie se enteraría.
--
-- Por eso las filas internas van en 901+. Cuando llegue BogData, sus códigos
-- entran en su propio rango y se puede mapear sin pisar nada.
--
-- ADITIVA Y NO DESTRUCTIVA: una columna nullable en `contrato` y filas nuevas
-- en un catálogo vacío. No altera ni borra nada existente.

BEGIN;

-- Las formas de pago que se usan en los contratos de un FDL. INTERNAS: no
-- pretenden ser el catálogo oficial de Hacienda, y por eso el rango 901+.
INSERT INTO forma_pago (codigo, nombre) VALUES
    (901, 'Pago único'),
    (902, 'Pagos mensuales'),
    (903, 'Pagos por avance o hitos'),
    (904, 'Anticipo y saldo'),
    (905, 'Contra entrega')
ON CONFLICT (codigo) DO NOTHING;

-- Nullable: NULL = «pendiente por diligenciar», que es lo que la pantalla dice.
-- Nunca se asume una forma de pago por defecto.
ALTER TABLE contrato
    ADD COLUMN IF NOT EXISTS forma_pago_codigo integer;

-- Las tres van juntas por el mismo motivo que las de la etapa: este dato lo
-- escribe UNA PERSONA sobre información contractual. Sin fecha ni autor, el
-- dato no se puede defender.
ALTER TABLE contrato
    ADD COLUMN IF NOT EXISTS forma_pago_fecha timestamptz;
ALTER TABLE contrato
    ADD COLUMN IF NOT EXISTS forma_pago_usuario_id integer;

-- FK al catálogo. `NOT VALID` a propósito: no revalida las 25 filas
-- existentes (todas en NULL), así que el ALTER no bloquea la tabla.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'contrato_forma_pago_fk'
    ) THEN
        ALTER TABLE contrato
            ADD CONSTRAINT contrato_forma_pago_fk
            FOREIGN KEY (forma_pago_codigo) REFERENCES forma_pago(codigo)
            NOT VALID;
    END IF;
END $$;

COMMENT ON COLUMN contrato.forma_pago_codigo IS
    'FK a forma_pago. NULL = pendiente. 901+ son internas; BogData usará su propio rango.';

COMMIT;
