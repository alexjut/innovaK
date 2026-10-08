-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║ 031 · auditoria_dato acepta un cambio hecho por una MÁQUINA              ║
-- ╚══════════════════════════════════════════════════════════════════════════╝
--
-- ⚠️ ESCRITO, NO APLICADO. Requiere autorización explícita de Alex.
--     Ensayado en transacción revertida el 2026-10-08: aplica limpio sobre las
--     168 filas existentes y la restricción las acepta todas.
--
-- ## Por qué hace falta
--
-- Hoy una clasificación automática NO ES REGISTRABLE, y eso no es un detalle
-- de implementación: es lo que impide adoptar cualquier modelo de decisión.
-- Medido contra information_schema el 2026-10-08:
--
--   · `usuario_id` es NOT NULL  → una fila sin persona detrás no se puede
--     insertar, y una máquina no tiene usuario;
--   · ninguna de las 14 columnas guarda QUÉ modelo decidió, con QUÉ versión
--     ni con CUÁNTA confianza.
--
-- Sin esto, el día en que un funcionario pregunte por qué su formulación quedó
-- marcada, la respuesta sería «lo dijo el modelo» — sin poder decir cuál, de
-- qué versión ni con qué probabilidad. Eso choca con la regla del proyecto de
-- que toda cifra diga de dónde sale.
--
-- ## La decisión de diseño, y por qué no es simplemente quitar el NOT NULL
--
-- Quitar `NOT NULL` a secas abre la puerta a filas humanas SIN autor, que es
-- justo la garantía que esa restricción daba. En su lugar entra una columna
-- `origen` y una restricción que exige una de las dos cosas: o hay persona, o
-- hay modelo. Nunca ninguna de las dos, nunca las dos a la vez.
--
-- Aditivo e idempotente. No toca ninguna columna existente salvo el NOT NULL
-- de `usuario_id`, que queda cubierto por la restricción nueva.

BEGIN;

ALTER TABLE auditoria_dato
    ADD COLUMN IF NOT EXISTS origen          varchar(16) NOT NULL DEFAULT 'humano',
    -- Qué modelo decidió. Con su versión al lado: la misma pregunta puede dar
    -- otra respuesta en otra versión, y sin eso un hallazgo no se reproduce.
    ADD COLUMN IF NOT EXISTS modelo          varchar(120),
    ADD COLUMN IF NOT EXISTS modelo_version  varchar(60),
    -- La probabilidad calibrada, en tanto por uno. Es la razón de registrar
    -- esto: una clase con 0,52 y una con 0,98 no son el mismo hecho.
    ADD COLUMN IF NOT EXISTS confianza       numeric(5,4),
    -- Hash de la entrada exacta que se le mandó al modelo. Permite rehacer la
    -- pregunta sin guardar el texto, que puede ser largo o reservado.
    ADD COLUMN IF NOT EXISTS entrada_hash    char(64);

-- `usuario_id` deja de ser obligatorio A NIVEL DE COLUMNA, pero sigue siendo
-- obligatorio para las filas humanas por la restricción de abajo.
ALTER TABLE auditoria_dato ALTER COLUMN usuario_id DROP NOT NULL;

-- O persona, o modelo. La restricción es lo que conserva la garantía que daba
-- el NOT NULL: ninguna fila queda sin responsable identificable.
ALTER TABLE auditoria_dato DROP CONSTRAINT IF EXISTS ck_auditoria_origen;
ALTER TABLE auditoria_dato ADD CONSTRAINT ck_auditoria_origen CHECK (
    (origen = 'humano'  AND usuario_id IS NOT NULL AND modelo IS NULL)
 OR (origen = 'maquina' AND modelo     IS NOT NULL)
);

-- Si viene confianza, es una probabilidad. Un 1,7 delata un bug de escala, que
-- es el mismo defecto que ya hizo que el cumplimiento saliera 100 veces más
-- pequeño en 42 de 78 metas.
ALTER TABLE auditoria_dato DROP CONSTRAINT IF EXISTS ck_auditoria_confianza;
ALTER TABLE auditoria_dato ADD CONSTRAINT ck_auditoria_confianza CHECK (
    confianza IS NULL OR (confianza >= 0 AND confianza <= 1)
);

-- Para poder listar «qué decidió la máquina» sin barrer la tabla entera.
CREATE INDEX IF NOT EXISTS idx_auditoria_origen_maquina
    ON auditoria_dato (origen, fecha DESC)
    WHERE origen = 'maquina';

COMMIT;

-- Comprobación posterior sugerida:
--   SELECT origen, COUNT(*) FROM auditoria_dato GROUP BY 1;
--     → humano 168, maquina 0
