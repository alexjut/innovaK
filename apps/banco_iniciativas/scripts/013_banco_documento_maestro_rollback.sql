-- ============================================================================
-- Rollback de 013_banco_documento_maestro.sql
--
-- ⚠️  LEER ANTES DE CORRER
--   Esto NO es un "deshacer" inocuo. Si el formulario nuevo ya recibió
--   postulaciones, este script BORRA dato que solo tiene el ciudadano:
--   problemática, justificación, objetivos, cronograma, equipo, presupuesto
--   y —lo más caro— el ORDEN DE ACTIVACIÓN de los enfoques de §7.8, que es
--   lo que liquida 10 de los 100 puntos y no se puede reconstruir.
--
--   Antes de correrlo:
--       SELECT count(*) FROM inscripcion_banco_presupuesto;
--       SELECT count(*) FROM inscripcion_banco_enfoque_familia;
--   Si devuelven > 0, saque backup y confirme con Alex que se puede perder.
--
--   Lo que este rollback NO deshace a propósito:
--     · Las filas sembradas en catálogos EXISTENTES (rango_experiencia,
--       rango_poblacion_atendida, tipo_beneficio_alk, nivel_educativo,
--       escenario). Borrarlas rompería la FK de cualquier inscripción que ya
--       las use. Se revierte el activo=FALSE de las viejas y se apagan las
--       nuevas; las filas se quedan.
--     · El ensanche de nombre_espacio_ejecucion / direccion_espacio_ejecucion.
--       Volver a VARCHAR(50) truncaría texto ya guardado. Se deja ancho.
-- ============================================================================

BEGIN;

-- ── D. Tablas hijas (orden inverso por dependencias) ──
DROP TABLE IF EXISTS inscripcion_banco_anexo;
DROP TABLE IF EXISTS inscripcion_banco_presupuesto;
DROP TABLE IF EXISTS inscripcion_banco_cronograma;
DROP TABLE IF EXISTS inscripcion_banco_equipo;
DROP TABLE IF EXISTS inscripcion_banco_actividad;
DROP TABLE IF EXISTS inscripcion_banco_objetivo_especifico;
DROP TABLE IF EXISTS inscripcion_banco_enfoque_opcion;
DROP TABLE IF EXISTS inscripcion_banco_enfoque_familia;
DROP TABLE IF EXISTS inscripcion_banco_instancia;

-- ── C. Columnas de cabecera ──
DROP INDEX IF EXISTS idx_insc_banco_ejecucion_ubicada;

ALTER TABLE inscripcion_banco_iniciativa
    DROP CONSTRAINT IF EXISTS fk_insc_banco_modalidad_actividad,
    DROP CONSTRAINT IF EXISTS fk_insc_banco_modalidad_propuesta,
    DROP CONSTRAINT IF EXISTS fk_insc_banco_disciplina_actividad,
    DROP CONSTRAINT IF EXISTS fk_insc_banco_arraigo_red,
    DROP CONSTRAINT IF EXISTS fk_insc_banco_ejecucion_red,
    DROP CONSTRAINT IF EXISTS fk_insc_banco_beneficio_alk,
    DROP CONSTRAINT IF EXISTS ck_insc_banco_arraigo_estrato,
    DROP CONSTRAINT IF EXISTS ck_insc_banco_ejecucion_estrato,
    DROP CONSTRAINT IF EXISTS ck_insc_banco_ejecucion_estrato_ideca,
    DROP CONSTRAINT IF EXISTS ck_insc_banco_tamano_staff_num,
    DROP CONSTRAINT IF EXISTS ck_insc_banco_arraigo_lonlat,
    DROP CONSTRAINT IF EXISTS ck_insc_banco_ejecucion_lonlat,
    DROP CONSTRAINT IF EXISTS ck_insc_banco_cobertura_staff,
    DROP CONSTRAINT IF EXISTS ck_insc_banco_cobertura_comunidad,
    DROP CONSTRAINT IF EXISTS ck_insc_banco_cobertura_indirectos,
    DROP CONSTRAINT IF EXISTS ck_insc_banco_diversidad_genero,
    DROP CONSTRAINT IF EXISTS ck_insc_banco_sostenibilidad;

ALTER TABLE inscripcion_banco_iniciativa
    DROP COLUMN IF EXISTS tiene_sede_fisica,
    DROP COLUMN IF EXISTS tamano_staff_num,
    DROP COLUMN IF EXISTS modalidad_actividad_codigo,
    DROP COLUMN IF EXISTS disciplina_actividad_codigo,
    DROP COLUMN IF EXISTS disciplina_actividad_otro,
    DROP COLUMN IF EXISTS arraigo_red_codigo,
    DROP COLUMN IF EXISTS arraigo_escenario_otro,
    DROP COLUMN IF EXISTS arraigo_espacio_nombre,
    DROP COLUMN IF EXISTS arraigo_direccion,
    DROP COLUMN IF EXISTS arraigo_lon,
    DROP COLUMN IF EXISTS arraigo_lat,
    DROP COLUMN IF EXISTS arraigo_estrato,
    DROP COLUMN IF EXISTS arraigo_actividad,
    DROP COLUMN IF EXISTS beneficio_alk_codigo,
    DROP COLUMN IF EXISTS problematica,
    DROP COLUMN IF EXISTS justificacion,
    DROP COLUMN IF EXISTS objetivo_general,
    DROP COLUMN IF EXISTS modalidad_propuesta_codigo,
    DROP COLUMN IF EXISTS cobertura_staff,
    DROP COLUMN IF EXISTS cobertura_comunidad,
    DROP COLUMN IF EXISTS cobertura_indirectos,
    DROP COLUMN IF EXISTS diversidad_genero_propuesta,
    DROP COLUMN IF EXISTS ejecucion_red_codigo,
    DROP COLUMN IF EXISTS ejecucion_escenario_otro,
    DROP COLUMN IF EXISTS ejecucion_estrato,
    DROP COLUMN IF EXISTS ejecucion_estrato_ideca,
    DROP COLUMN IF EXISTS ejecucion_lon,
    DROP COLUMN IF EXISTS ejecucion_lat,
    DROP COLUMN IF EXISTS ejecucion_fuera_kennedy,
    DROP COLUMN IF EXISTS ejecucion_geo_metodo,
    DROP COLUMN IF EXISTS sostenibilidad_ambiental,
    DROP COLUMN IF EXISTS sostenibilidad_sustento,
    DROP COLUMN IF EXISTS metodologia,
    DROP COLUMN IF EXISTS declaracion_buena_fe,
    DROP COLUMN IF EXISTS radicado_at;

-- ── B. Catálogos existentes: se revierte el interruptor, NO se borran filas.
UPDATE rango_experiencia        SET activo = TRUE  WHERE codigo BETWEEN 1 AND 5;
UPDATE rango_experiencia        SET activo = FALSE WHERE codigo BETWEEN 6 AND 10;
UPDATE rango_poblacion_atendida SET activo = TRUE  WHERE codigo BETWEEN 1 AND 4;
UPDATE rango_poblacion_atendida SET activo = FALSE WHERE codigo BETWEEN 5 AND 8;
UPDATE tipo_beneficio_alk       SET activo = FALSE WHERE codigo IN (7, 8);
UPDATE escenario SET activo = FALSE
 WHERE nombre IN ('Colegios privados', 'Canchas sintéticas con cerramiento');

-- ── A. Catálogos nuevos (ya sin nada que los referencie) ──
DROP TABLE IF EXISTS banco_enfoque_opcion;
DROP TABLE IF EXISTS banco_enfoque_familia;
DROP TABLE IF EXISTS instancia_concertacion;
DROP TABLE IF EXISTS modalidad_recreodeportiva;

COMMIT;
