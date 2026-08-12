-- 003 — Migra los marcadores de `presu_avance_ind_periodo.observaciones` al
--       formato delimitado `[clave=valor]`.
--
-- NO ES DDL: no cambia el schema, solo reescribe el texto de 6 filas.
-- Aun así lo aplica Alex, porque escribe sobre la base compartida.
--
-- POR QUÉ. El marcador iba suelto (`infra_contrato=102`) y se buscaba con
-- `LIKE '%…%'`, que empareja por prefijo: buscar el contrato 10 encuentra el
-- 102, el 103 y el 104. En infraestructura eso es un UPDATE que pisa el avance
-- de otro contrato sin dejar rastro, y los contratos 1 y 10 ya existen: basta
-- con que alguno se marque VIAS o PARQUES. Delimitar lo cierra.
--
-- POR QUÉ MIGRAR EN VEZ DE TOLERAR LOS DOS FORMATOS. Tolerar el viejo obliga a
-- conservar para siempre la búsqueda ambigua que es justamente el defecto que
-- se cierra. A cambio se ahorra este UPDATE de 6 filas sobre una tabla de 7.
--
-- ⚠️ ORDEN DE APLICACIÓN: este script corre ANTES de desplegar el código
-- nuevo. Si se despliega primero, `sincronizar_kpi` no reconocería sus filas
-- viejas y CREARÍA duplicados que el KPI (agregación SUMA) contaría dos veces.
--
-- Verificado el 2026-08-12: 7 filas en la tabla, 6 con marcador.

BEGIN;

-- Antes: 'infra_contrato=102; unidades terminadas (seguimiento infraestructura)'
-- Después: '[infra_contrato=102] unidades terminadas (seguimiento infraestructura)'
UPDATE presu_avance_ind_periodo
   SET observaciones = '[infra_contrato=' || split_part(split_part(observaciones, 'infra_contrato=', 2), ';', 1) || '] '
                       || btrim(split_part(observaciones, ';', 2)),
       updated_at    = now()
 WHERE observaciones LIKE 'infra_contrato=%';

-- Antes: 'festival=4;acto=89'  →  Después: '[festival=4][acto=89]'
UPDATE presu_avance_ind_periodo
   SET observaciones = '[festival=' || split_part(split_part(observaciones, 'festival=', 2), ';', 1) || ']'
                       || '[acto='  || split_part(observaciones, 'acto=', 2) || ']',
       updated_at    = now()
 WHERE observaciones LIKE 'festival=%';

-- Comprobación: no debe quedar ninguna fila con marcador sin delimitar.
DO $$
DECLARE sueltas INTEGER;
BEGIN
    SELECT count(*) INTO sueltas
      FROM presu_avance_ind_periodo
     WHERE observaciones IS NOT NULL
       AND observaciones ~ '(^|[^[])(infra_contrato|festival|acto|captura|entrega_beca|entrega_insumo)=';
    IF sueltas > 0 THEN
        RAISE EXCEPTION 'Quedaron % filas con marcador sin delimitar', sueltas;
    END IF;
END $$;

COMMIT;
