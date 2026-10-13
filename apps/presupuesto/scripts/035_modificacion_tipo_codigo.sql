-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║ 035 · secop_modificacion.tipo_codigo — la grafía del origen cambió        ║
-- ╚══════════════════════════════════════════════════════════════════════════╝
--
-- ✅ APLICADO el 2026-10-13, encabezado corregido en el MISMO movimiento.
--    Comprobado después de aplicar: el relleno de SQL y la función de Python
--    dan el MISMO resultado en los 12 valores distintos del espejo.
--
-- ## Qué pasó
--
-- El 2026-10-13, al extender el espejo a 2020, la ingesta trajo el `tipo` del
-- dataset `cb9c-h8sn` con OTRA grafía. Hoy la tabla tiene las dos a la vez:
--
--     Modificacion General   4.949      MODIFICACION GENERAL     18
--     Suspensión               555      SUSPENSIoN                1
--     Reactivación             679      REACTIVACIoN              2
--     Cesion                   399      CESION                    7
--
-- Las 28 filas viejas son las que el origen ya no publica, así que la mezcla es
-- permanente: no se va a «arreglar» en la próxima corrida.
--
-- La API pública no se rompió, porque su `tipo_codigo` se calcula en Python con
-- un normalizador que quita tildes y unifica —y su propio comentario decía
-- «rompería al consumidor cada vez que el origen la cambie, y acaba de
-- cambiarla»—. Lo que SÍ se rompió es todo el SQL que comparaba el literal:
--
--     metadatos.py       WHERE tipo IN ('SUSPENSIoN','REACTIVACIoN')  → 3 filas de 1.234
--     ficha_api_publica  WHERE tipo = 'CESION'                        → 7 filas de 406
--     la prueba del eje  el mismo IN                                  → medía sobre nada
--
-- Ninguno falló: todos devolvieron un número más chico con cara de correcto.
--
-- ## Por qué una columna y no arreglar los tres sitios
--
-- Arreglar los tres deja la llave viviendo en Python, y cualquier consulta
-- nueva vuelve a nacer comparando el literal —que es exactamente lo que acaba
-- de pasar—. Con la columna, el SQL tiene a qué agarrarse y el normalizador
-- sigue siendo uno solo: la ingesta la llena importando la MISMA función que usa
-- la API, no una copia.
--
-- El literal del origen se queda en `tipo`, intacto, para poder trazar contra
-- datos.gov.co.
--
-- Rollback: rollback_035_modificacion_tipo_codigo.sql

BEGIN;

ALTER TABLE secop_modificacion
    ADD COLUMN IF NOT EXISTS tipo_codigo varchar(60);

COMMENT ON COLUMN secop_modificacion.tipo_codigo IS
    'El `tipo` normalizado: sin tildes, en mayúsculas y con guión bajo por '
    'espacio (Suspensión y SUSPENSIoN → SUSPENSION). Es lo que debe usar '
    'cualquier consulta; `tipo` guarda el literal del origen, que cambia de '
    'grafía. Lo llena la ingesta con apps.publico.services.modificaciones._codigo.';

-- Relleno inicial. Replica al normalizador de Python en el orden exacto:
-- espacios a guión bajo, quitar tildes, mayúsculas. Se comprueba contra la
-- función de Python valor por valor después de aplicar.
UPDATE secop_modificacion
   SET tipo_codigo = upper(translate(
           regexp_replace(trim(tipo), '\s+', '_', 'g'),
           'áàäâéèëêíìïîóòöôúùüûñçÁÀÄÂÉÈËÊÍÌÏÎÓÒÖÔÚÙÜÛÑÇ',
           'aaaaeeeeiiiioooouuuuncAAAAEEEEIIIIOOOOUUUUNC'))
 WHERE tipo IS NOT NULL
   AND tipo_codigo IS NULL;

CREATE INDEX IF NOT EXISTS idx_secop_mod_tipo_codigo
    ON secop_modificacion (tipo_codigo) WHERE tipo_codigo IS NOT NULL;

COMMIT;
