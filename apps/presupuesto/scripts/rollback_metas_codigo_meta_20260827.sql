-- Deshace el enganche de 8 metas internas con su código SEGPLAN oficial,
-- escrito el 2026-08-27 por `sdp_mapear_codigo_meta --apply`.
--
-- Se escribió ANTES de la aprobación explícita que pide la Constitución VII:
-- la guarda de firma que lo habría impedido quedó sin crear porque la llamada
-- que la agregaba fue bloqueada, y la corrida siguiente ya no tenía nada que
-- la frenara. Los valores en sí están verificados uno por uno (contención 1.00
-- con margen sobre la 2ª candidata), pero la decisión de escribirlos no era mía.
--
-- Backup vigente al momento de la escritura:
--   ~/Proyectos/postgres/backups/poblacion_kennedy_diario.dump (2026-08-27 02:00)
--
-- Revierte a NULL, que es exactamente el estado anterior de esas 8 filas.
UPDATE metas SET codigo_meta = NULL
 WHERE codigo IN (7, 100023, 100024, 100025, 100026, 100027, 100028, 100029);
