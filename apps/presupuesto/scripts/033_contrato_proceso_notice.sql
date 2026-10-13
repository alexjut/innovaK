-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║ 033 · secop_contrato.proceso_notice_id — la llave que conecta con el PAA  ║
-- ╚══════════════════════════════════════════════════════════════════════════╝
--
-- ✅ APLICADO el 2026-10-13, y este encabezado se corrigió en el MISMO
--    movimiento. Siete scripts de este repo quedaron mintiendo por no hacerlo,
--    y eso costó que llegara un encargo para construir un módulo que ya existía.
--    Backup del día: 12 h de antigüedad al aplicar.
--
-- ## El problema: CO1.BDOS y CO1.NTC son DOS identificadores distintos
--
-- Un contrato de SECOP arrastra dos identificadores de su proceso, y confundirlos
-- cuesta un día entero:
--
--     secop_contrato.proceso_de_compra ....... CO1.BDOS.7099614
--     url_proceso → ?noticeUID= .............. CO1.NTC.7117690
--
-- No son el mismo número ni se derivan uno del otro: medido el 2026-10-13 sobre
-- los 3.211 contratos, coinciden en CERO casos. Y cada uno sirve para una cosa:
--
--     el dataset de ARCHIVOS (dmgg-8hin) se consulta por `proceso` = CO1.BDOS
--       (probado: CO1.BDOS.7099614 devuelve 1 fila; CO1.NTC.7117690 devuelve 0)
--     el PAA (9sue-ezhx) solo trae la URL, o sea CO1.NTC
--
-- `proceso_de_compra` ya está en la tabla y al 100 %. Lo que falta es el otro, que
-- hoy vive enterrado dentro de una URL de 150 caracteres: para cruzar el PAA hay
-- que hacerle `substring` con una expresión regular a 3.211 filas en cada consulta.
--
-- ## Lo que se midió antes de escribir esto (2026-10-13)
--
--     contratos con noticeUID extraíble de la URL ....... 3.211  (100,0 %)
--     prefijo: CO1.NTC en todos
--     noticeUID distintos ...............................  2.480
--     noticeUID con más de un contrato ..................    328
--
-- Y el cruce con el PAA de Kennedy (6.579 filas, 2017-2026), en las DOS
-- direcciones, porque son dos cifras distintas y confundirlas es el error que
-- ya produjo una cobertura del 160 % en este proyecto:
--
--     de los 1.806 procesos del PAA, están en nuestro espejo .. 96,4 %
--     de nuestros 3.211 contratos, están en el PAA ............ 70,5 %
--       2024 ....  344 / 1.135 ....  30,3 %   ← el PAA de 2024 casi no declaró proceso
--       2025 .. 1.181 / 1.184 ....  99,7 %
--       2026 ....  728 /   872 ....  83,5 %
--
-- El techo es de la fuente, no nuestro: solo 29,0 % de las filas del PAA de
-- Kennedy declaran un proceso. Las otras quedaron en «No Definido».
--
-- ## Por qué una columna y no un índice funcional
--
-- Un índice sobre `substring(url_proceso from ...)` resolvería la consulta, pero
-- la llave seguiría invisible: nadie que mire la tabla sabría que existe, y el
-- próximo que necesite cruzar el PAA la volvería a extraer a mano con su propia
-- expresión regular —que es como nacen dos llaves que no coinciden—.
--
-- Rollback: rollback_033_contrato_proceso_notice.sql

BEGIN;

ALTER TABLE secop_contrato
    ADD COLUMN IF NOT EXISTS proceso_notice_id varchar(60);

COMMENT ON COLUMN secop_contrato.proceso_notice_id IS
    'Identificador del AVISO del proceso (CO1.NTC.*), extraído del parámetro '
    'noticeUID de url_proceso. Es la llave para cruzar con el PAA (9sue-ezhx), '
    'que solo publica la URL. NO es proceso_de_compra (CO1.BDOS.*), que es la '
    'llave del dataset de archivos (dmgg-8hin): no coinciden en ningún caso.';

-- Relleno inicial. La misma expresión que usa la ingesta, para que no haya dos
-- formas de extraer la misma llave.
UPDATE secop_contrato
   SET proceso_notice_id = substring(url_proceso from 'noticeUID=([A-Za-z0-9._-]+)')
 WHERE proceso_notice_id IS NULL
   AND url_proceso IS NOT NULL;

-- No es UNIQUE: 328 noticeUID tienen más de un contrato. Un proceso puede
-- adjudicar varios contratos y eso es normal, no un duplicado.
CREATE INDEX IF NOT EXISTS idx_secop_contrato_notice
    ON secop_contrato (proceso_notice_id)
 WHERE proceso_notice_id IS NOT NULL;

COMMIT;
