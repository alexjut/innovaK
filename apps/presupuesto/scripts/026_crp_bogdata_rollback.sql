-- Rollback del DDL 026.
--
-- ABORTA si hay cargas registradas: revertir los tipos de `crp` a `integer`
-- con datos adentro TRUNCARÍA los valores que desbordan (hay filas de
-- $25.884 M contra un tope de $2.147 M). Vaciar primero es una decisión que
-- tiene que tomar una persona, no un script.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM crp_carga LIMIT 1) THEN
        RAISE EXCEPTION
          'Hay cargas de CRP registradas. Revertir los tipos truncaría valores '
          'que no caben en integer. Vaciá crp y crp_carga a mano si de verdad '
          'querés revertir.';
    END IF;
END $$;

BEGIN;

DROP INDEX IF EXISTS uq_crp_interno_posicion;
DROP INDEX IF EXISTS idx_crp_carga;
DROP INDEX IF EXISTS idx_crp_contrato;
DROP INDEX IF EXISTS idx_crp_proyecto;
DROP INDEX IF EXISTS idx_crp_tercero;
DROP INDEX IF EXISTS idx_crp_rubro;
DROP INDEX IF EXISTS idx_crp_compromiso;
DROP INDEX IF EXISTS idx_crp_vigente;

ALTER TABLE crp
    DROP COLUMN IF EXISTS carga_id,
    DROP COLUMN IF EXISTS tercero_id,
    DROP COLUMN IF EXISTS compromiso_numero,
    DROP COLUMN IF EXISTS compromiso_anio,
    DROP COLUMN IF EXISTS tipo_compromiso_desc,
    DROP COLUMN IF EXISTS rubro_desc,
    DROP COLUMN IF EXISTS fondo_desc,
    DROP COLUMN IF EXISTS modalidad_desc,
    DROP COLUMN IF EXISTS texto_id_proyecto,
    DROP COLUMN IF EXISTS programa_financiamiento,
    DROP COLUMN IF EXISTS fecha_inicio_compromiso,
    DROP COLUMN IF EXISTS fecha_fin_compromiso,
    DROP COLUMN IF EXISTS es_obligacion_por_pagar,
    DROP COLUMN IF EXISTS es_funcionamiento,
    DROP COLUMN IF EXISTS vigente,
    DROP COLUMN IF EXISTS created_at,
    DROP COLUMN IF EXISTS updated_at;

ALTER TABLE rubro
    DROP COLUMN IF EXISTS tipo,
    DROP COLUMN IF EXISTS proyecto_cod;

DROP TABLE IF EXISTS tercero_sap;
DROP TABLE IF EXISTS crp_carga;

-- Los tipos de `crp` NO se revierten. Volver `valor_neto` a integer es
-- exactamente el defecto que el 026 vino a corregir, y dejarlo así no rompe
-- nada: una columna BIGINT acepta todo lo que aceptaba la integer.

COMMIT;
