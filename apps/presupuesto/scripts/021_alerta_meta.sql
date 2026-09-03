-- 021 · Alerta de cumplimiento por meta — la columna «Alerta» de la hoja
-- «Alertas» de la Matriz de seguimiento PDL
--
-- POR QUÉ. La ALK pide un filtro de proyectos por estado de ejecución
-- (Crítico / En ejecución de acuerdo a cronograma / Ejecutada / Desierta / Sin
-- magnitud contratada). Esa taxonomía YA vive en el Excel que manda la ALK
-- —hoja «Alertas», tabla de detalle en A68:G146, 78 metas evaluadas— pero
-- hoy no está en ningún lado de la base (verificado: cero referencias a
-- "Desierta" / "Sin magnitud contratada" en todo el repo, backend y
-- frontend). No hay dato que filtrar hasta que esto se cargue.
--
-- QUÉ TRAE la hoja, por meta:
--   Proyecto (código-nombre) | Meta (texto) | Contratada | Ejecutada |
--   Cumplimiento % | Diferencia | Alerta
-- con Alerta calculada por umbral de Cumplimiento % —salvo Desierta/Sin
-- magnitud, que son categorías propias y no un umbral— y publicada como
-- texto ya resuelto, no como fórmula: se importa el VALOR, no se
-- reconstruye la regla acá.
--
-- DÓNDE VIVE. Mismas cuatro filas de identidad que la plata: por
-- `codigo_meta` + `vigencia` + `fuente`, en la MISMA tabla que ya trae la
-- apropiación de esta fuente (DDL 020) — es el mismo cargue, la misma
-- fila por meta, así que son columnas nuevas, no una tabla nueva. La
-- vigencia es 2025 porque el título de la hoja lo dice expresamente
-- («Alertas de cumplimiento de metas 2025»); cuando la ALK mande el corte
-- de otro trimestre o año, se carga como una fila más con su propia
-- vigencia — el UNIQUE (codigo_meta, vigencia, fuente) ya lo permite sin
-- pisar nada.
--
-- `magnitud_contratada` / `magnitud_ejecutada` / `cumplimiento_pct` viajan
-- junto con `alerta` y no solo la palabra: sin la base y el ejecutado el
-- frontend no puede explicar POR QUÉ una meta salió «Crítico» — solo
-- podría repetir la palabra.
--
-- ADITIVO: agrega columnas a una tabla existente, no crea nada nuevo ni
-- toca datos de otras fuentes. Rollback en rollback_021_alerta_meta.sql
-- (dropea las cuatro columnas).

BEGIN;

ALTER TABLE presu_presupuesto_meta_vigencia
    ADD COLUMN IF NOT EXISTS alerta              VARCHAR(40),
    ADD COLUMN IF NOT EXISTS magnitud_contratada  NUMERIC(14,2),
    ADD COLUMN IF NOT EXISTS magnitud_ejecutada   NUMERIC(14,2),
    ADD COLUMN IF NOT EXISTS cumplimiento_pct     NUMERIC(7,4);

-- Constraint blanda, no ENUM: si la ALK agrega una categoría nueva en un
-- corte futuro, un valor fuera de la lista se reporta por el importador
-- (que sí valida) en vez de que un CHECK tumbe todo el cargue de ese
-- trimestre por una fila.
CREATE INDEX IF NOT EXISTS idx_presup_meta_vig_alerta
    ON presu_presupuesto_meta_vigencia (alerta)
    WHERE alerta IS NOT NULL;

COMMENT ON COLUMN presu_presupuesto_meta_vigencia.alerta IS
    'Alerta de cumplimiento de la meta, valor ya resuelto por la ALK (no '
    'recalculado acá): Crítico | En ejecución de acuerdo a cronograma | Ejecutada | '
    'Desierta | Sin magnitud contratada. Fuente: hoja «Alertas» de la Matriz '
    'PDL, columna G. Se importa con importar_alerta_metas_pdl.';
COMMENT ON COLUMN presu_presupuesto_meta_vigencia.magnitud_contratada IS
    'Columna «Contratada» de la hoja Alertas: la base contra la que se mide '
    'el cumplimiento de la meta.';
COMMENT ON COLUMN presu_presupuesto_meta_vigencia.magnitud_ejecutada IS
    'Columna «Ejecutada» de la hoja Alertas.';
COMMENT ON COLUMN presu_presupuesto_meta_vigencia.cumplimiento_pct IS
    'Columna «Cumplimiento %» de la hoja Alertas (magnitud_ejecutada / '
    'magnitud_contratada, ya calculado por la ALK).';

COMMIT;
