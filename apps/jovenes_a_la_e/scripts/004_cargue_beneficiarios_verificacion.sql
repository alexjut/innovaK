-- Verificación de 004 — correr DESPUÉS de aplicar.
--
-- Son cuatro consultas y cada una tiene un resultado esperado explícito. Si
-- alguna no da lo que dice, NO sigas: el DDL quedó a medias.
--
--   docker exec innova_k python -c "
--   import django,os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
--   django.setup()
--   from django.db import connection
--   c=connection.cursor()
--   c.execute(open('apps/jovenes_a_la_e/scripts/004_cargue_beneficiarios_verificacion.sql').read())
--   [print(r) for r in c.fetchall()]"
--
-- (ese cursor solo muestra el resultado de la ÚLTIMA consulta; para verlas
--  todas, córrelas una por una o usa el bloque de una sola salida del final)

-- ── 1 · Las cinco columnas nuevas ───────────────────────────────────────
-- Esperado: 5 filas. vigencia smallint NOT NULL con default; origen
-- varchar NOT NULL default 'QR'; los dos SNIES varchar(20) nullables;
-- cargue_id bigint nullable.
SELECT column_name, data_type, character_maximum_length AS largo,
       is_nullable, column_default
  FROM information_schema.columns
 WHERE table_name = 'entrega_beca'
   AND column_name IN ('vigencia', 'origen', 'snies_programa', 'snies_ies', 'cargue_id')
 ORDER BY column_name;

-- ── 2 · La llave nueva está y la vieja NO ───────────────────────────────
-- Esperado: EXACTAMENTE una fila, `uq_entrega_beca_matricula`, y su
-- definición debe contener NULLS NOT DISTINCT. Si aparece
-- `uq_entrega_beca_evento_doc`, el DROP no corrió.
SELECT indexname, indexdef
  FROM pg_indexes
 WHERE tablename = 'entrega_beca'
   AND indexname IN ('uq_entrega_beca_matricula', 'uq_entrega_beca_evento_doc');

-- ── 3 · La tabla del lote, con su índice parcial ────────────────────────
-- Esperado: 14 columnas y el índice único `uq_cargue_hash_vigencia` con su
-- WHERE (estado <> 'anulado').
SELECT (SELECT count(*) FROM information_schema.columns
         WHERE table_name = 'cargue_beneficiarios')                AS columnas_lote,
       (SELECT indexdef FROM pg_indexes
         WHERE indexname = 'uq_cargue_hash_vigencia')              AS indice_hash,
       (SELECT count(*) FROM pg_constraint
         WHERE conname = 'fk_entrega_beca_cargue')                 AS fk_cargue;

-- ── 4 · Los CHECK y el flag del tipo de evento ──────────────────────────
-- Esperado: vigencia >= 2024, origen IN ('QR','CARGA') y
-- requiere_actividad_plan = true para JOVENES_BECA.
SELECT (SELECT pg_get_constraintdef(oid) FROM pg_constraint
         WHERE conname = 'ck_entrega_beca_vigencia')               AS check_vigencia,
       (SELECT pg_get_constraintdef(oid) FROM pg_constraint
         WHERE conname = 'ck_entrega_beca_origen')                 AS check_origen,
       (SELECT requiere_actividad_plan FROM tipo_evento
         WHERE codigo = 'JOVENES_BECA')                            AS becas_exige_plan;

-- ── Todo en una sola salida (cómodo para el cursor de Django) ───────────
-- Esperado: las cinco columnas en TRUE.
SELECT
    (SELECT count(*) = 5 FROM information_schema.columns
      WHERE table_name = 'entrega_beca'
        AND column_name IN ('vigencia','origen','snies_programa','snies_ies','cargue_id'))
                                                                   AS columnas_ok,
    (SELECT count(*) = 1 FROM pg_indexes
      WHERE indexname = 'uq_entrega_beca_matricula'
        AND indexdef ILIKE '%NULLS NOT DISTINCT%')                 AS llave_matricula_ok,
    (SELECT count(*) = 0 FROM pg_indexes
      WHERE indexname = 'uq_entrega_beca_evento_doc')              AS llave_vieja_borrada,
    (SELECT to_regclass('public.cargue_beneficiarios') IS NOT NULL) AS tabla_lote_ok,
    (SELECT requiere_actividad_plan FROM tipo_evento
      WHERE codigo = 'JOVENES_BECA')                               AS becas_exige_plan;
