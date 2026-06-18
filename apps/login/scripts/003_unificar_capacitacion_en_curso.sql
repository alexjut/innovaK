-- =====================================================================
-- Unifica el tipo de evento CAPACITACION dentro de CURSO (decisión Alex
-- 2026-06-18: "dejar uno solo, quitar CAPACITACION para que no haya confusión").
-- Ambos van al mismo panel (/app/cursos) y mis_cursos_de_docente ya los trata
-- juntos. Migra los eventos y desactiva el tipo (reversible, NO hard-delete).
--
-- APLICAR tras backup < 24 h (hay backup diario 02:00). El contenedor innova_k
-- NO tiene psql: aplicar con
--   connection.cursor().execute(open('.../003_unificar_capacitacion_en_curso.sql').read())
-- REVERSA al final.
-- =====================================================================
BEGIN;

-- 1) Re-apunta los eventos CAPACITACION → CURSO (hoy: 5 eventos de Seguridad,
--    sin sector_caracterizacion → su inscripción cae al form genérico gracias
--    al fix data-driven en _url_publica_por_tipo).
UPDATE evento SET tipo_evento_codigo = 'CURSO'
 WHERE tipo_evento_codigo = 'CAPACITACION';

-- 2) Desactiva el tipo CAPACITACION (desaparece de todas las UIs, que filtran
--    activo=TRUE). Se conserva la fila por historia; reversible.
UPDATE tipo_evento SET activo = FALSE WHERE codigo = 'CAPACITACION';

COMMIT;

-- Verificación esperada:
--   SELECT count(*) FROM evento WHERE tipo_evento_codigo='CAPACITACION';  -- 0
--   SELECT activo FROM tipo_evento WHERE codigo='CAPACITACION';           -- f

-- =====================================================================
-- REVERSA (si hay que deshacer): no se puede recuperar qué eventos eran
-- CAPACITACION una vez migrados (todos quedan CURSO). Para reactivar el tipo:
--   UPDATE tipo_evento SET activo = TRUE WHERE codigo = 'CAPACITACION';
-- =====================================================================
