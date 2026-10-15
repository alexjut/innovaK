-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║ 037 · formulacion_transicion.rol_requerido — quién puede mover qué        ║
-- ╚══════════════════════════════════════════════════════════════════════════╝
--
-- ✅ APLICADO el 2026-10-15, encabezado corregido en el MISMO movimiento.
--    Respaldo del día: 9 h de antigüedad al aplicar.
--
-- ## El hueco que cierra
--
-- `formulacion.cambiar_estado()` tiene tres guardas —la transición existe, el
-- estado no es final, no se pasa a contratación con un requisito crítico
-- pendiente— y recibe `usuario`. Pero NADIE comprueba quién es ese usuario.
--
-- Hoy, cualquiera que alcance el endpoint puede mover cualquier formulación a
-- cualquier estado válido. Incluido APROBAR LA PROPIA: la transición
-- «En revisión → Aprobada» no pide nada. Eso es un hallazgo de control interno,
-- no una comodidad.
--
-- ## Los carriles, dichos por la Alcaldía (2026-10-15)
--
-- El flujo real tiene TRES carriles, no los cinco que proponían los documentos
-- entregados (que añadían Planeación y Comité):
--
--     1. FORMULADOR     el líder del subgrupo, que en la base es la familia
--                       `Coordinador*`. El subgrupo sale de CUÁL grupo
--                       coordinador sea: `CoordinadorDeportes` formula para
--                       Deportes. No hace falta rol nuevo, y la maquinaria ya
--                       existe: `puede_crear_en_area` exige `es_coordinador`
--                       Y que el subgrupo esté en su alcance.
--     2. CONTRATACION   revisa según el estado.
--     3. PRESUPUESTO    al final.
--
-- ## Por qué el rol va en la TRANSICIÓN y no en el ESTADO
--
-- Porque no coinciden. Del estado «Con observaciones» sale una transición del
-- formulador —«pasar a Subsanando», o sea «me pongo a corregir»— mientras el
-- estado lo puso contratación. Un rol por estado obligaría a elegir uno de los
-- dos y dejaría al otro sin poder mover su propia parte.
--
-- ## El reparto de las 22, y de dónde sale
--
-- Se deriva de quién hace cada acto, no de un orden:
--
--     formulador    1→2, 2→3, 2→4, 3→4, 3→5, 4→3, 6→7, 7→5
--     contratacion  5→6, 5→8, 8→6
--     presupuesto   8→9, 9→6
--     cancelar      cada →10 va al carril DUEÑO del estado de origen
--
-- La cancelación no se le da a uno solo: cancelar desde «Borrador» es del
-- formulador y cancelar desde «En revisión» es de contratación. Dárselo todo a
-- un carril permitiría cancelar el trabajo de otro.
--
-- ## Lo que NO hace este script
--
-- No crea el grupo `Presupuesto`, que NO EXISTE en la base (los grupos de hoy
-- son Admin, Coordinador, CoordinadorDeportes, Docente, Gestor,
-- GestorEducacion, Lider, Lider_contrato, LiderInfraestructura,
-- LiderParticipacion, Planeacion, SeguimientoInfraestructura, UsuarioGeneral,
-- Visor). Crearlo es un acto explícito: `seed_rol_formulacion`.
--
-- Hasta que exista, la transición «Aprobada → Lista para contratación» la puede
-- hacer SOLO un superusuario, porque la guarda niega por defecto. Ese es el
-- fallo seguro: que no se pueda avanzar es visible; que cualquiera apruebe, no.
--
-- ⚠ Y una advertencia que ya costó caro en este repo: el grupo nuevo NO puede
--   llamarse empezando por «Coordinador». `es_coordinador()` compara por
--   PREFIJO, así que `CoordinadorPresupuesto` heredaría poder de creación en
--   áreas sin que nadie lo decida.
--
-- Rollback: rollback_037_formulacion_rol_requerido.sql

BEGIN;

ALTER TABLE formulacion_transicion
    ADD COLUMN IF NOT EXISTS rol_requerido varchar(30);

COMMENT ON COLUMN formulacion_transicion.rol_requerido IS
    'Carril que puede ejecutar esta transición: formulador, contratacion o '
    'presupuesto. NULL significa que nadie salvo un superusuario puede hacerla '
    '—la guarda niega por defecto—, no que sea libre.';

-- ── El reparto ───────────────────────────────────────────────────────────────
-- Los estados se identifican por `orden`, que es lo que usa `formulacion_transicion`.

-- Formulador: construir, pedir información, retomar y someter a revisión.
UPDATE formulacion_transicion SET rol_requerido = 'formulador'
 WHERE (origen, destino) IN ((1,2), (2,3), (2,4), (3,4), (3,5), (4,3));

-- Formulador: aceptar las observaciones y volver a someter.
UPDATE formulacion_transicion SET rol_requerido = 'formulador'
 WHERE (origen, destino) IN ((6,7), (7,5));

-- Contratación: revisar. Devolver con observaciones, aprobar, o reabrir una
-- aprobada que no debió aprobarse.
UPDATE formulacion_transicion SET rol_requerido = 'contratacion'
 WHERE (origen, destino) IN ((5,6), (5,8), (8,6));

-- Presupuesto: el acto final y su devolución.
UPDATE formulacion_transicion SET rol_requerido = 'presupuesto'
 WHERE (origen, destino) IN ((8,9), (9,6));

-- Cancelar: cada una al carril dueño del estado de origen.
UPDATE formulacion_transicion SET rol_requerido = 'formulador'
 WHERE destino = 10 AND origen IN (1, 2, 3, 4, 7);
UPDATE formulacion_transicion SET rol_requerido = 'contratacion'
 WHERE destino = 10 AND origen IN (5, 6);
UPDATE formulacion_transicion SET rol_requerido = 'presupuesto'
 WHERE destino = 10 AND origen IN (8, 9);

-- Que no quede ninguna sin carril: una transición con `rol_requerido` NULL
-- queda inalcanzable salvo para un superusuario, y si eso pasa por olvido en
-- vez de por decisión, el flujo se tranca sin que nadie sepa por qué.
DO $$
DECLARE n integer;
BEGIN
    SELECT COUNT(*) INTO n FROM formulacion_transicion WHERE rol_requerido IS NULL;
    IF n > 0 THEN
        RAISE EXCEPTION 'Quedaron % transiciones sin rol_requerido', n;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_formulacion_transicion_rol
    ON formulacion_transicion (rol_requerido);

COMMIT;
