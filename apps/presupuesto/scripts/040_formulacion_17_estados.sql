-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║ 040 · El catálogo de estados pasa de 10 a 17                              ║
-- ╚══════════════════════════════════════════════════════════════════════════╝
--
-- ✅ APLICADO el 2026-10-15, encabezado corregido en el MISMO movimiento.
--    Respaldo del día: 13 h. Las 6 formulaciones existentes siguen en el
--    estado 1 (Borrador), que es 1 en los dos modelos: no se remapeó ninguna.
--
-- ## De dónde salen los 17
--
-- Alex decidió el 2026-10-15: «vamos con 17», sobre la base de las Historias de
-- Usuario y completado según análisis. Los 17 son la tabla de estados del
-- Manual —16 estados con su responsable y su salida típica— más CANCELADA, que
-- el Manual no lista porque no es parte del camino sino su interrupción.
--
-- Los 10 de hoy eran una versión corta y genérica (Borrador, En elaboración, En
-- formulación, Pendiente de información, En revisión, Con observaciones,
-- Subsanando, Aprobada, Lista para contratación, Cancelada). El camino real
-- tiene dos revisiones distintas —Planeación y Contratos/Jurídica—, un paso por
-- comité y dos actos de presupuesto, y con un solo «En revisión» no se puede
-- saber quién tiene el expediente.
--
-- ## Los 17, con el carril que los mueve
--
--      1 Borrador                      formulador
--      2 En formulación                formulador
--      3 Validación de Planeación      contratacion   ← revisión
--      4 Observaciones de Planeación    formulador     ← observación
--      5 Planeación validada           contratacion
--      6 Revisión de Contratos         contratacion   ← revisión
--      7 Observaciones de Contratos    formulador     ← observación
--      8 Validado jurídicamente        contratacion
--      9 Solicitud de comité           formulador
--     10 En comité                     contratacion   ← revisión
--     11 Ajustes de comité             formulador     ← observación
--     12 Comité aprobado               contratacion
--     13 Pendiente de CDP              presupuesto
--     14 CDP registrado                presupuesto
--     15 Listo para publicación        presupuesto
--     16 Publicado                     presupuesto    ← final
--     17 Cancelada                     —              ← final
--
-- ## Por qué TRES carriles y no los cinco del documento
--
-- El Manual reparte entre cinco responsables: Área de origen, Planeación,
-- Contratos/Jurídica, Comité y Presupuesto. Alex dijo que en la práctica son
-- tres: el líder de subgrupo formula, contratación revisa según el estado, y
-- presupuesto va al final.
--
-- Así que los estados del documento se CONSERVAN —describen el camino
-- administrativo real— y se asignan a los tres carriles que existen:
-- Planeación y Comité quedan bajo `contratacion`, que es quien revisa hoy. Si
-- mañana Planeación o Comité se vuelven carriles propios, es un UPDATE sobre
-- `formulacion_transicion.rol_requerido` y un grupo nuevo: por eso el rol vive
-- en la transición y no en el código.
--
-- ## Las dos banderas nuevas, y por qué hacen falta
--
-- Las compuertas de las observaciones (DDL 039) se anclaban al NOMBRE del
-- estado: «Con observaciones» y «En revisión». En el modelo de 17 hay TRES
-- revisiones y TRES estados de observación, así que un nombre ya no alcanza y
-- un número tampoco —se mueven—. Se clasifican con banderas:
--
--     es_revision     el expediente está en manos de quien revisa
--     es_observacion  volvió al formulador con algo que corregir
--
-- ## El dato que ya existe
--
-- 6 formulaciones, todas en estado 1 (Borrador), que sigue siendo 1 en el
-- modelo nuevo: no hay que remapear ninguna. Cero requisitos marcados, cero
-- documentos, cero observaciones. Es el momento de hacer este cambio; con el
-- expediente andando no lo sería.
--
-- Rollback: rollback_040_formulacion_17_estados.sql

BEGIN;

-- ── 1 · Las banderas de clasificación ───────────────────────────────────────
ALTER TABLE formulacion_estado
    ADD COLUMN IF NOT EXISTS es_revision    boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS es_observacion boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS carril         varchar(30);

COMMENT ON COLUMN formulacion_estado.es_revision IS
    'El expediente está en manos de quien revisa. Lo usan las compuertas de '
    'observaciones en vez del nombre del estado: con 17 estados hay TRES '
    'revisiones y un nombre ya no alcanza.';
COMMENT ON COLUMN formulacion_estado.es_observacion IS
    'Volvió al formulador con algo que corregir. Son tres: de Planeación, de '
    'Contratos y de comité.';
COMMENT ON COLUMN formulacion_estado.carril IS
    'Carril que mueve el expediente DESDE este estado. Informativo: el que '
    'manda es `formulacion_transicion.rol_requerido`, porque de un mismo '
    'estado pueden salir transiciones de carriles distintos.';

-- ── 2 · Fuera las transiciones viejas ───────────────────────────────────────
-- Se borran antes de tocar los estados: referencian `orden`, y dejarlas
-- apuntando a órdenes que cambian de significado sería peor que no tenerlas.
DELETE FROM formulacion_transicion;

-- ── 3 · Los 17 ──────────────────────────────────────────────────────────────
-- `codigo` = `orden` como ya era. Se hace UPSERT para no romper la FK de las 6
-- formulaciones existentes, que están todas en el 1.
--
-- Antes hay que LIBERAR LOS NOMBRES: la tabla tiene un UNIQUE sobre `nombre` y
-- varios nombres se reusan con otro código —«En formulación» era el 3 y pasa a
-- ser el 2—. Sin este paso el upsert por `codigo` choca contra el nombre que
-- todavía tiene su dueño anterior, y el error no dice eso: dice «duplicate key
-- (nombre)», que parece un nombre repetido en la lista nueva.
UPDATE formulacion_estado SET nombre = '__liberando_' || codigo;

INSERT INTO formulacion_estado
    (codigo, nombre, orden, es_final, bloquea_contratacion,
     es_revision, es_observacion, carril, descripcion)
VALUES
    ( 1, 'Borrador',                   1, false, true,  false, false, 'formulador',
      'Se está creando. No ha salido del área.'),
    ( 2, 'En formulación',             2, false, true,  false, false, 'formulador',
      'El área diligencia las casillas y adjunta soportes.'),
    ( 3, 'Validación de Planeación',   3, false, true,  true,  false, 'contratacion',
      'En revisión de Planeación.'),
    ( 4, 'Observaciones de Planeación',4, false, true,  false, true,  'formulador',
      'Devuelta por Planeación con observaciones.'),
    ( 5, 'Planeación validada',        5, false, true,  false, false, 'contratacion',
      'Planeación la validó; sigue a Contratos.'),
    ( 6, 'Revisión de Contratos',      6, false, true,  true,  false, 'contratacion',
      'En revisión de Contratos/Jurídica.'),
    ( 7, 'Observaciones de Contratos', 7, false, true,  false, true,  'formulador',
      'Devuelta por Contratos con observaciones.'),
    ( 8, 'Validado jurídicamente',     8, false, true,  false, false, 'contratacion',
      'Revisión jurídica superada.'),
    ( 9, 'Solicitud de comité',        9, false, true,  false, false, 'formulador',
      'El área solicita el comité.'),
    (10, 'En comité',                 10, false, true,  true,  false, 'contratacion',
      'Sometida al comité.'),
    (11, 'Ajustes de comité',         11, false, true,  false, true,  'formulador',
      'El comité pidió ajustes.'),
    (12, 'Comité aprobado',           12, false, true,  false, false, 'contratacion',
      'El comité aprobó; sigue a presupuesto.'),
    (13, 'Pendiente de CDP',          13, false, false, false, false, 'presupuesto',
      'A la espera del CDP. Desde acá el expediente ya sale a contratación, '
      'así que es el estado que exige la completitud.'),
    (14, 'CDP registrado',            14, false, false, false, false, 'presupuesto',
      'El CDP quedó registrado y relacionado.'),
    (15, 'Listo para publicación',    15, false, false, false, false, 'presupuesto',
      'Listo para publicar el proceso.'),
    (16, 'Publicado',                 16, true,  false, false, false, 'presupuesto',
      'Publicado. Fin del camino.'),
    (17, 'Cancelada',                 17, true,  true,  false, false, NULL,
      'Interrumpida. De acá no se sale.')
ON CONFLICT (codigo) DO UPDATE SET
    nombre = EXCLUDED.nombre, orden = EXCLUDED.orden,
    es_final = EXCLUDED.es_final,
    bloquea_contratacion = EXCLUDED.bloquea_contratacion,
    es_revision = EXCLUDED.es_revision,
    es_observacion = EXCLUDED.es_observacion,
    carril = EXCLUDED.carril, descripcion = EXCLUDED.descripcion;

-- ── 4 · Las transiciones, con su carril ─────────────────────────────────────
-- Camino adelante, tal como lo describe la tabla del Manual.
INSERT INTO formulacion_transicion (origen, destino, rol_requerido) VALUES
    ( 1,  2, 'formulador'),     -- Borrador → En formulación
    ( 2,  3, 'formulador'),     -- somete a Planeación
    ( 3,  4, 'contratacion'),   -- Planeación observa
    ( 3,  5, 'contratacion'),   -- Planeación valida
    ( 4,  3, 'formulador'),     -- el área atiende y resomete
    ( 5,  6, 'contratacion'),   -- pasa a Contratos
    ( 6,  7, 'contratacion'),   -- Contratos observa
    ( 6,  8, 'contratacion'),   -- Contratos valida
    ( 7,  6, 'formulador'),     -- el área atiende y resomete
    ( 8,  9, 'contratacion'),   -- habilita la solicitud de comité
    ( 9, 10, 'formulador'),     -- el área solicita el comité
    (10, 11, 'contratacion'),   -- el comité pide ajustes
    (10, 12, 'contratacion'),   -- el comité aprueba
    (11, 10, 'formulador'),     -- el área ajusta y vuelve al comité
    (12, 13, 'contratacion'),   -- sigue a presupuesto
    (13, 14, 'presupuesto'),    -- registra el CDP
    (14, 15, 'presupuesto'),    -- queda listo para publicar
    (15, 16, 'presupuesto'),    -- publica
    -- Retornos desde presupuesto: una no aprobación conserva el expediente y
    -- lo devuelve, igual que hacían 8→6 y 9→6 en el modelo de 10.
    (13,  7, 'presupuesto'),
    (15,  7, 'presupuesto');

-- Cancelar: desde cada estado no final, y al carril DUEÑO de ese estado.
-- Dárselo a uno solo permitiría cancelar el trabajo de otro.
INSERT INTO formulacion_transicion (origen, destino, rol_requerido)
SELECT e.orden, 17, e.carril
  FROM formulacion_estado e
 WHERE NOT e.es_final AND e.carril IS NOT NULL;

-- ── 5 · Coherencia, comprobada acá y no después ─────────────────────────────
DO $$
DECLARE n integer; faltan text;
BEGIN
    SELECT COUNT(*) INTO n FROM formulacion_estado;
    IF n <> 17 THEN RAISE EXCEPTION 'Quedaron % estados, no 17', n; END IF;

    SELECT COUNT(*) INTO n FROM formulacion_transicion WHERE rol_requerido IS NULL;
    IF n > 0 THEN RAISE EXCEPTION '% transiciones sin carril', n; END IF;

    -- Todo estado no final tiene salida: si no, el expediente se tranca ahí.
    SELECT string_agg(e.nombre, ', ') INTO faltan
      FROM formulacion_estado e
     WHERE NOT e.es_final
       AND NOT EXISTS (SELECT 1 FROM formulacion_transicion t WHERE t.origen = e.orden);
    IF faltan IS NOT NULL THEN
        RAISE EXCEPTION 'Estados sin salida: %', faltan;
    END IF;

    -- Todo estado no inicial es alcanzable: si no, es un estado muerto.
    SELECT string_agg(e.nombre, ', ') INTO faltan
      FROM formulacion_estado e
     WHERE e.orden <> 1
       AND NOT EXISTS (SELECT 1 FROM formulacion_transicion t WHERE t.destino = e.orden);
    IF faltan IS NOT NULL THEN
        RAISE EXCEPTION 'Estados inalcanzables: %', faltan;
    END IF;

    -- De un estado final no sale nada.
    SELECT COUNT(*) INTO n FROM formulacion_transicion t
      JOIN formulacion_estado e ON e.orden = t.origen WHERE e.es_final;
    IF n > 0 THEN RAISE EXCEPTION 'Salen % transiciones de un estado final', n; END IF;

    -- Y ninguna formulación quedó apuntando a un estado que no existe.
    SELECT COUNT(*) INTO n FROM formulacion f
     WHERE NOT EXISTS (SELECT 1 FROM formulacion_estado e WHERE e.codigo = f.estado_codigo);
    IF n > 0 THEN RAISE EXCEPTION '% formulaciones en un estado inexistente', n; END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_formulacion_estado_clase
    ON formulacion_estado (es_revision, es_observacion);

COMMIT;
